"""Where the pipeline's output and the reference text disagree, and the verdicts on them.

A disagreement is one differing stretch in the word alignment of output and
reference, located on the scan through the paragraph's source lines. A verdict
records what the scan actually prints there. It is keyed on the reference words
and their context, so it still applies after the pipeline changes.

Verdicts live in git, one JSON object per line, in
`golden/<name>/verdicts/<scan id>.jsonl`; a later line overrides an earlier one.
"""

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from rapidfuzz.distance import Levenshtein

from roboscriptorium.evaluate import normalise
from roboscriptorium.golden.reference import Chapter
from roboscriptorium.ir import Document, SourceRef
from roboscriptorium.pdf import PageText

CONTEXT_WORDS = 6
# Differing stretches at most this many matching words apart are one disagreement.
MERGE_GAP = 1
WORD_LIST = Path("/usr/share/dict/words")
# Characters a printed English book's text consists of.
_PRINTABLE = re.compile(r"^[A-Za-zÀ-ÿœæŒÆ0-9 .,;:!?'\"—()\-&£]*$")

# Verdict categories. The first group are pipeline mistakes (the reference is
# right); the second are places where the scan really prints something else.
PIPELINE = {
    "ocr": "OCR misread",
    "artefact": "Print artefact kept (running head, page number, stamp)",
    "lost": "Body text lost",
    "hyphen": "Hyphenation or word joining",
    "punctuation": "Punctuation or spacing",
    "other": "Other pipeline mistake",
}
SCAN = {
    "edition": "Edition difference: the scan prints this",
    "transcriber": "Gutenberg changed or corrected the print",
}
UNSURE = "unsure"


@dataclass(frozen=True)
class Disagreement:
    key: str
    got: str  # output words
    want: str  # reference words
    before: str  # reference context
    after: str
    page: int | None
    lines: tuple[int, int] | None  # first and last line index on that page
    # A pipeline mistake category when the output is clearly garbled and needs no review.
    auto: str | None = None


@dataclass(frozen=True)
class Verdict:
    key: str
    before: str
    want: str
    after: str
    got: str
    truth: str | None  # what the scan prints; None while unsure
    category: str
    page: int | None
    note: str = ""
    at: str = ""


def _key(before: list[str], want: list[str], after: list[str]) -> str:
    blob = json.dumps([before, want, after], ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def _word_sources(doc: Document, pages: dict[int, PageText]) -> tuple[list[str], list[SourceRef]]:
    """Output words, each with the source line it most likely came from."""
    words, refs = [], []
    for para in doc.paragraphs:
        para_words = normalise(para.text).split()
        if not para_words:
            continue
        sources = para.sources or [None]
        counts = [
            max(1, len(normalise(pages[s.page].lines[s.line].text).split())) if s else 1
            for s in sources
        ]
        # Reflow joins hyphenated words and drops artefacts, so spread the
        # paragraph's words over its lines in proportion to their word counts.
        scale = sum(counts) / len(para_words)
        bounds, total = [], 0
        for c in counts:
            total += c
            bounds.append(total)
        k = 0
        for i, w in enumerate(para_words):
            while k < len(bounds) - 1 and i * scale >= bounds[k]:
                k += 1
            words.append(w)
            refs.append(sources[k])
    return words, refs


def reference_words(reference: list[Chapter]) -> list[str]:
    return [w for ch in reference for p in ch.paragraphs for w in normalise(p).split()]


def vocabulary(reference: list[Chapter]) -> set[str]:
    words = {w.lower() for w in WORD_LIST.read_text().split()} if WORD_LIST.exists() else set()
    for ch in reference:
        for para in ch.paragraphs:
            words.update(w.lower() for w in re.findall(r"[^\W\d_]+", para))
    return words


def garbled(text: str, vocab: set[str]) -> bool:
    """Output that no printed page says: stray symbols, or a word not in the vocabulary."""
    if not _PRINTABLE.match(text):
        return True
    return any(w.lower() not in vocab for w in re.findall(r"[^\W\d_]+", text))


def _auto(got: str, want: str, vocab: set[str]) -> str | None:
    if got.replace(" ", "") == want.replace(" ", ""):
        return "punctuation"
    if got and garbled(got, vocab):
        return "ocr"
    return None


def _spans(out: list[str], ref: list[str]) -> list[tuple[int, int, int, int]]:
    """Differing stretches as (out start, out end, ref start, ref end), close ones merged."""
    spans: list[list[int]] = []
    for op in Levenshtein.opcodes(out, ref):
        if op.tag == "equal":
            continue
        if (
            spans
            and op.src_start - spans[-1][1] <= MERGE_GAP
            and (op.dest_start - spans[-1][3] <= MERGE_GAP)
        ):
            spans[-1][1], spans[-1][3] = op.src_end, op.dest_end
        else:
            spans.append([op.src_start, op.src_end, op.dest_start, op.dest_end])
    return [tuple(s) for s in spans]


def find(doc: Document, reference: list[Chapter], pages: list[PageText]) -> list[Disagreement]:
    out, refs = _word_sources(doc, {p.number: p for p in pages})
    ref = reference_words(reference)
    vocab = vocabulary(reference)
    found = []
    for s0, s1, d0, d1 in _spans(out, ref):
        before = ref[max(0, d0 - CONTEXT_WORDS) : d0]
        want = ref[d0:d1]
        after = ref[d1 : d1 + CONTEXT_WORDS]
        got = " ".join(out[s0:s1])
        span = [r for r in refs[s0:s1] if r is not None]
        if not span:
            near = [refs[i] for i in (s0 - 1, s0) if 0 <= i < len(refs)]
            span = [r for r in near if r is not None]
        page = span[0].page if span else None
        on_page = [r.line for r in span if r.page == page]
        found.append(
            Disagreement(
                key=_key(before, want, after),
                got=got,
                want=" ".join(want),
                before=" ".join(before),
                after=" ".join(after),
                page=page,
                lines=(min(on_page), max(on_page)) if on_page else None,
                auto=_auto(got, " ".join(want), vocab),
            )
        )
    return found


class Verdicts:
    def __init__(self, path: Path):
        self.path = path
        self.by_key: dict[str, Verdict] = {}
        if path.exists():
            for line in path.read_text().splitlines():
                if line.strip():
                    v = Verdict(**json.loads(line))
                    self.by_key[v.key] = v

    def record(self, d: Disagreement, truth: str | None, category: str, note: str = "") -> Verdict:
        v = Verdict(
            d.key,
            d.before,
            d.want,
            d.after,
            d.got,
            truth,
            category,
            d.page,
            note,
            datetime.now(UTC).isoformat(timespec="seconds"),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps(asdict(v), ensure_ascii=False) + "\n")
        self.by_key[v.key] = v
        return v


def _find_sequence(words: list[str], seq: list[str]) -> int | None:
    n = len(seq)
    for i in range(len(words) - n + 1):
        if words[i : i + n] == seq:
            return i
    return None


def _printed(para: str) -> list[tuple[str, str]]:
    """The paragraph's words, normalised and as printed."""
    words, printed = normalise(para).split(), para.split()
    return list(zip(words, printed if len(printed) == len(words) else words, strict=True))


def patch(reference: list[Chapter], verdicts: Verdicts) -> tuple[list[Chapter], int]:
    """The reference with each verdict's truth put in where the scan differs from it.

    Returns the patched chapters and how many verdicts were applied.
    """
    # (chapter, paragraph, word, italic, printed) for every reference word, in order:
    # verdicts match on the normalised word, the chapters keep the word as printed.
    flat = [
        (c, p, w, k in (ch.italic[p] if p < len(ch.italic) else ()), printed)
        for c, ch in enumerate(reference)
        for p, para in enumerate(ch.paragraphs)
        for k, (w, printed) in enumerate(_printed(para))
    ]
    # Each verdict's context is the unpatched reference's, so all are found before any
    # is applied: a verdict a few words from another still matches.
    words = [w for _, _, w, _, _ in flat]
    found = []
    for v in verdicts.by_key.values():
        if v.truth is None or v.truth == v.want:
            continue
        before, want, after = v.before.split(), v.want.split(), v.after.split()
        at = _find_sequence(words, before + want + after)
        if at is not None:
            found.append((at + len(before), len(want), v.truth.split()))
    applied = 0
    # Right to left, so each leaves the positions before it in place; a verdict
    # overlapping one already applied is skipped.
    taken = len(flat) + 1
    for start, size, truth in sorted(found, key=lambda f: (-f[0], -f[1])):
        if start + size > taken:
            continue
        c, p, _, italic, _ = (
            (flat[start] if size else flat[max(0, start - 1)]) if flat else (0, 0, "", False, "")
        )
        flat[start : start + size] = [(c, p, w, italic, w) for w in truth]
        taken = start
        applied += 1

    chapters = []
    for c, ch in enumerate(reference):
        paragraphs: dict[int, list[tuple[str, bool]]] = {}
        for cc, p, _, italic, printed in flat:
            if cc == c:
                paragraphs.setdefault(p, []).append((printed, italic))
        words = [ws for _, ws in sorted(paragraphs.items())]
        chapters.append(
            Chapter(
                ch.heading,
                [" ".join(w for w, _ in ws) for ws in words],
                [frozenset(k for k, (_, italic) in enumerate(ws) if italic) for ws in words],
            )
        )
    return chapters, applied
