"""Check a scan's OCR text layer against a second reading, line by line.

Two more readings of each body line: glm-ocr on the line's crop (best on
letters and words) and tesseract on the page (best on dashes). Where either
differs from the text layer (widened to whole words), the role model picks a
version from the crop of the scan, and a text model picks the version of the
line that reads right. When both pick the same reading and the role model is at least somewhat
sure, it is applied; any other suspect is left to a human.

Fixes go into a copy of the pages, matched on the text layer's line text, so
the line texts the review keys its answers on stay as they are. Born-digital
PDFs, whose text is exact, aren't checked.
"""

import base64
import csv
import hashlib
import io
import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

import httpx
import pymupdf
from rapidfuzz.distance import Levenshtein

from roboscriptorium import ocr
from roboscriptorium.clients import ollaya
from roboscriptorium.clients.ollaya import OllayaClient
from roboscriptorium.files import write_atomic
from roboscriptorium.ir import SourceRef
from roboscriptorium.lexicon import Lexicon
from roboscriptorium.pdf import PageText, line_words, spells
from roboscriptorium.reflow import HYPHENS
from roboscriptorium.roles import DecisionCache

DPI = 300
READING_VERSION = 2
READ_WORKERS = 4
# Points above and below a line's crop for the OCR model. Crops also reach one em (the
# line's height) past each end, where a dash or quote the text layer missed is printed.
LINE_PAD = 3
MAX_LINE_TOKENS = 120
# Readings are written to the cache every so many lines, so a long run keeps its progress.
SAVE_EVERY = 200
TESSERACT_VERSION = 1
TESSERACT_WORKERS = 6
# The role model must be at least this sure, and agree with the text model.
SURE = 0.3
# Where versions differ only in punctuation, dashes or spacing, the text model can't
# tell them apart; the vision model decides alone when at least this sure.
SURE_ALONE = 0.5
CROP_ZOOM = 4
CROP_PAD = 4  # points around the suspect words
# Lines shorter than this are page numbers and scraps, not worth a second reading.
MIN_LINE_CHARS = 12
# Curly quotes as straight ones, and a not sign (some OCR layers' line-end hyphen) as a
# hyphen, one character for one, so offsets stay put.
_FOLD = str.maketrans("‘’“”¬", "''\"\"-")
_OPENING_QUOTES = re.compile(r"(^|\s)[\"'‘’“”]+")
_SPACE_BEFORE_APOSTROPHE = re.compile(r"(?<=\w) +'(?=\w)")
LANGUAGE_NAMES = {"nld": "Dutch", "eng": "English"}


@dataclass(frozen=True)
class Suspect:
    page: int
    line: int  # index into the text layer's lines
    original: str  # the line as the text layer reads it
    start: int  # the differing words, as a span of `original`
    end: int
    ours: str
    others: tuple[str, ...]  # the other readings of the span
    box: tuple[float, float, float, float]
    choice: str  # "ours", "other" (then `chosen` says which), or "review"
    chosen: str | None = None
    # Each model's pick: a version of the span (`ours` or one of `others`), or "".
    votes: dict[str, str] = field(default_factory=dict)
    # Each model's confidence in its pick.
    confidence: dict[str, float] = field(default_factory=dict)

    @property
    def alternatives(self) -> list[str]:
        """The line as each other reading has it."""
        return [self.original[: self.start] + o + self.original[self.end :] for o in self.others]


def scanned(pdf: Path, sample: int = 10) -> bool:
    """Whether the text layer is invisible OCR over page images (not born-digital text)."""
    invisible = visible = 0
    with pymupdf.open(pdf) as doc:
        step = max(1, doc.page_count // sample)
        for page in list(doc)[::step]:
            for span in page.get_texttrace():
                if span["type"] == 3:
                    invisible += len(span["chars"])
                else:
                    visible += len(span["chars"])
    return invisible > visible


def line_readings(
    pdf: Path,
    pages: list[PageText],
    checked: set[SourceRef],
    model: str,
    ollama_url: str,
    cache: Path,
) -> dict[SourceRef, str]:
    """The OCR model's reading of each checked line's crop, cached on the line's text."""
    done: dict[str, str] = {}
    if cache.exists():
        raw = json.loads(cache.read_text())
        if raw.get("version") == READING_VERSION and raw.get("model") == model:
            done = raw["lines"]

    with pymupdf.open(pdf) as doc:
        boxes = {p.number: line_boxes(doc[p.number - 1], p) for p in pages}

    def key(page: PageText, k: int) -> str:
        text = hashlib.sha1(page.lines[k].text.encode()).hexdigest()[:10]
        box = ",".join(f"{v:.0f}" for v in boxes[page.number][k])
        return f"{page.number}:{k}:{text}:{box}"

    wanted = {
        SourceRef(p.number, k): (p, k)
        for p in pages
        for k, line in enumerate(p.lines)
        if SourceRef(p.number, k) in checked and len(line.text) >= MIN_LINE_CHARS
    }
    todo = [(p, k) for p, k in wanted.values() if key(p, k) not in done]

    def save() -> None:
        blob = {"version": READING_VERSION, "model": model, "lines": done}
        write_atomic(cache, json.dumps(blob, ensure_ascii=False))

    # PyMuPDF isn't thread-safe: crops are rendered here, a batch at a time, and
    # only the model calls run in the pool.
    with pymupdf.open(pdf) as doc, ThreadPoolExecutor(READ_WORKERS) as pool:
        for start in range(0, len(todo), SAVE_EVERY):
            batch = todo[start : start + SAVE_EVERY]
            crops = [_line_crop(doc, page.number, boxes[page.number][k]) for page, k in batch]
            texts = pool.map(lambda png: read_line(png, model, ollama_url), crops)
            for (page, k), text in zip(batch, texts, strict=True):
                done[key(page, k)] = text
            save()
    return {ref: done[key(p, k)] for ref, (p, k) in wanted.items()}


def tesseract_readings(
    pdf: Path, pages: list[PageText], checked: set[SourceRef], lang: str, cache: Path
) -> dict[SourceRef, str]:
    """Tesseract's reading of each checked line: its words whose centres fall in the line."""
    words = tesseract_words(pdf, [p.number for p in pages], lang, cache)
    with pymupdf.open(pdf) as doc:
        boxes = {p.number: line_boxes(doc[p.number - 1], p) for p in pages}
    out = {}
    for page in pages:
        for k, found in enumerate(_by_line(boxes[page.number], words[page.number])):
            ref = SourceRef(page.number, k)
            if ref in checked and len(page.lines[k].text) >= MIN_LINE_CHARS:
                out[ref] = " ".join(w[0] for w in found)
    return out


def tesseract_words(
    pdf: Path, numbers: list[int], lang: str, cache: Path
) -> dict[int, list[tuple[str, float, float, float, float]]]:
    """Tesseract's words with their boxes in points, per page, cached."""
    done: dict[int, list] = {}
    if cache.exists():
        raw = json.loads(cache.read_text())
        if raw.get("version") == TESSERACT_VERSION and raw.get("lang") == lang:
            done = {int(n): [tuple(w) for w in ws] for n, ws in raw["pages"].items()}
    todo = [n for n in numbers if n not in done]
    if todo:
        # Pages are rendered on this thread (PyMuPDF isn't thread-safe); tesseract runs pooled.
        with pymupdf.open(pdf) as doc, ThreadPoolExecutor(TESSERACT_WORKERS) as pool:
            for start in range(0, len(todo), TESSERACT_WORKERS):
                batch = todo[start : start + TESSERACT_WORKERS]
                images = [doc[n - 1].get_pixmap(dpi=DPI).tobytes("png") for n in batch]
                read = pool.map(lambda png: _tesseract_page(png, lang), images)
                for n, page_words in zip(batch, read, strict=True):
                    done[n] = page_words
        blob = {"version": TESSERACT_VERSION, "lang": lang, "pages": done}
        write_atomic(cache, json.dumps(blob, ensure_ascii=False))
    return {n: done[n] for n in numbers}


def _tesseract_page(png: bytes, lang: str) -> list[tuple[str, float, float, float, float]]:
    out = ocr.tesseract(png, lang, tsv=True)
    rows = csv.DictReader(io.StringIO(out), delimiter="\t", quoting=csv.QUOTE_NONE)
    if out and "level" not in (rows.fieldnames or []):
        raise ValueError(f"tesseract gave no word table: {out[:200]!r}")
    scale = 72 / DPI
    words = []
    for row in rows:
        text = (row.get("text") or "").strip()
        if row["level"] == "5" and text:
            x, y, w, h = (int(row[k]) * scale for k in ("left", "top", "width", "height"))
            words.append((text, x, y, x + w, y + h))
    return words


def _by_line(boxes: list, words) -> list[list[tuple[str, float, float, float, float]]]:
    """Tesseract's words per line: the nearest line box (widened a little) holding the centre."""
    out = [[] for _ in boxes]
    for w in words:
        cx, cy = (w[1] + w[3]) / 2, (w[2] + w[4]) / 2
        holding = [
            k
            for k, b in enumerate(boxes)
            if b[0] - 3 <= cx <= b[2] + 3 and b[1] - 2 <= cy <= b[3] + 2
        ]
        if holding:
            out[min(holding, key=lambda k: abs((boxes[k][1] + boxes[k][3]) / 2 - cy))].append(w)
    return [sorted(ws, key=lambda w: w[1]) for ws in out]


def _line_crop(doc: pymupdf.Document, number: int, box) -> bytes:
    em = box[3] - box[1]
    clip = pymupdf.Rect(box) + (-em, -LINE_PAD, em, LINE_PAD)
    return doc[number - 1].get_pixmap(dpi=DPI, clip=clip).tobytes("png")


def line_boxes(pdf_page: pymupdf.Page, page: PageText) -> list[tuple[float, float, float, float]]:
    """Each line's box as printed: its words' boxes together where they spell the line.

    Some OCR layers give lines boxes far taller than the print.
    """
    out = []
    for line, words in zip(page.lines, line_words(pdf_page.get_text("words"), page), strict=True):
        if words and spells(words, line.text):
            out.append(_union(words))
        else:
            out.append((line.x0, line.y0, line.x1, line.y1))
    return out


def _union(words) -> tuple[float, float, float, float]:
    return (
        min(w[0] for w in words),
        min(w[1] for w in words),
        max(w[2] for w in words),
        max(w[3] for w in words),
    )


def read_line(png: bytes, model: str, ollama_url: str) -> str:
    """The OCR model's reading of one printed line.

    glm-ocr's Ollama template has no stop token, so after the line it starts over;
    the reading ends at its first line break. It sometimes writes a printed em
    dash as the CJK character 一, which looks the same.
    """
    payload = {
        "model": model,
        "prompt": "Text Recognition:",
        "images": [base64.b64encode(png).decode()],
        "options": {"num_predict": MAX_LINE_TOKENS},
    }
    out = ""
    with httpx.stream("POST", f"{ollama_url}/api/generate", json=payload, timeout=300) as resp:
        resp.raise_for_status()
        for chunk in resp.iter_lines():
            if chunk:
                out += json.loads(chunk).get("response", "")
            if "\n" in out.strip():
                break
    return out.strip().split("\n")[0].strip().replace("一", "—")


def _word_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start > 0 and text[start - 1] != " ":
        start -= 1
    while end < len(text) and text[end] != " ":
        end += 1
    return start, end


def differences(ours: str, theirs: str) -> list[tuple[int, int, int, int]]:
    """Where two readings of a line differ, widened to whole words, as spans of each.

    Curly and straight quotes count as the same. A difference only in opening
    quote marks isn't one: OCR models read a printed “ as ‘, and no model can
    tell them apart in a crop. Nor is a reading without the space before an
    apostrophe ("uur’s" for "uur ’s"): OCR models miss the narrow space Dutch
    print sets before the article ’s, and no judge sees it in a crop.
    """
    spans = []
    for op in Levenshtein.opcodes(ours.translate(_FOLD), theirs.translate(_FOLD)):
        if op.tag == "equal":
            continue
        a = _word_span(ours, op.src_start, op.src_end)
        b = _word_span(theirs, op.dest_start, op.dest_end)
        if spans and a[0] <= spans[-1][1]:
            prev = spans.pop()
            a, b = (prev[0], max(prev[1], a[1])), (prev[2], max(prev[3], b[1]))
        spans.append((*a, *b))
    return [
        s
        for s in spans
        if _bare(ours[s[0] : s[1]]) != _bare(theirs[s[2] : s[3]])
        and ours[s[0] : s[1]].translate(_FOLD).strip()
        != theirs[s[2] : s[3]].translate(_FOLD).strip()
        and _SPACE_BEFORE_APOSTROPHE.sub("'", ours[s[0] : s[1]].translate(_FOLD))
        != theirs[s[2] : s[3]].translate(_FOLD)
    ]


def _bare(text: str) -> str:
    return _OPENING_QUOTES.sub(r"\1", text.translate(_FOLD)).strip()


def _box(words: list, box, original: str, start: int, end: int):
    """The suspect words' box: the text layer's word boxes, or a share of the line's box.

    At the line's start or end it reaches one em further, where a mark the text
    layer missed is printed.
    """
    k0 = original[:start].count(" ")
    k1 = k0 + original[start:end].strip().count(" ") + 1
    x0, y0, x1, y1 = box
    if spells(words, original):
        out = list(_union(words[k0:k1]))
    else:
        out = [x0 + (x1 - x0) * start / len(original), y0, x0 + (x1 - x0) * end / len(original), y1]
    em = y1 - y0
    if start == 0:
        out[0] -= em
    if end == len(original):
        out[2] += em
    return tuple(out)


def check(
    pdf: Path,
    pages: list[PageText],
    readings: list[dict[SourceRef, str]],
    lang: str,
    vision: OllayaClient,
    reader: OllayaClient,
    cache: DecisionCache,
    lexicon: Lexicon | None = None,
) -> list[Suspect]:
    """Suspects where any other reading differs from the text layer, each with a decision."""
    suspects = []
    with pymupdf.open(pdf) as doc:
        for page in pages:
            pdf_page = doc[page.number - 1]
            words = line_words(pdf_page.get_text("words"), page)
            boxes = line_boxes(pdf_page, page)
            for k, line in enumerate(page.lines):
                ours = line.text
                others = [r.get(SourceRef(page.number, k), "") for r in readings]
                for a0, a1, alternatives in merged_differences(ours, [o for o in others if o]):
                    box = _box(words[k], boxes[k], ours, a0, a1)
                    around = (
                        page.lines[k - 1].text if k > 0 else "",
                        page.lines[k + 1].text if k + 1 < len(page.lines) else "",
                    )
                    continues = a0 == 0 and k > 0 and page.lines[k - 1].text.endswith(HYPHENS)
                    (choice, chosen, votes), confidence = _decide(
                        pdf_page, page.number, k, ours, a0, a1, alternatives, box, lang,
                        vision, reader, cache, around,
                        lexicon.vouches([ours[a0:a1], *alternatives], continues)
                        if lexicon else None,
                    )  # fmt: skip
                    suspects.append(
                        Suspect(
                            page.number,
                            k,
                            ours,
                            a0,
                            a1,
                            ours[a0:a1],
                            tuple(alternatives),
                            box,
                            choice,
                            chosen,
                            votes,
                            confidence,
                        )  # fmt: skip
                    )
    return suspects


def merged_differences(ours: str, others: list[str]) -> list[tuple[int, int, list[str]]]:
    """Spans of `ours` where any other reading differs, with each distinct other version.

    Overlapping differences from different readings become one span; a reading
    that agrees with `ours` there has no version of its own.
    """
    found = [
        (a0, a1, b0, b1, r)
        for r, other in enumerate(others)
        for a0, a1, b0, b1 in differences(ours, other)
    ]
    groups: list[list] = []
    for d in sorted(found):
        if groups and d[0] <= max(g[1] for g in groups[-1]):
            groups[-1].append(d)
        else:
            groups.append([d])
    out = []
    for group in groups:
        g0, g1 = min(d[0] for d in group), max(d[1] for d in group)
        versions = []
        for r, other in enumerate(others):
            mine = sorted((d for d in group if d[4] == r), key=lambda d: -d[0])
            if not mine:
                continue
            piece = ours[g0:g1]
            for a0, a1, b0, b1, _ in mine:
                piece = piece[: a0 - g0] + other[b0:b1] + piece[a1 - g0 :]
            if _curly(ours):
                piece = _curled(piece)
            # Readings that differ only in quote style are one version.
            folded = [v.translate(_FOLD) for v in versions]
            if piece.translate(_FOLD) != ours[g0:g1].translate(_FOLD) and (
                piece.translate(_FOLD) not in folded
            ):
                versions.append(piece)
        if versions and (both := _combined(ours[g0:g1], versions)):
            versions.append(both)
        if versions:
            out.append((g0, g1, versions))
    return out


def _curly(text: str) -> bool:
    return any(c in text for c in "‘’“”") and not any(c in text for c in "'\"")


def _curled(text: str) -> str:
    """Straight quotes as curly ones: opening at a word's start, closing elsewhere."""
    text = re.sub(r"(^|\s)'", r"\1‘", text)
    text = re.sub(r"(^|\s)\"", r"\1“", text)
    return text.replace("'", "’").replace('"', "”")


_TRAILING = re.compile(r"^(.*?)([.,;:!?…]*)([’”'\"]*)$", re.S)


def _combined(ours: str, versions: list[str]) -> str | None:
    """The word with every reading's trailing marks, where each reading lost a different one.

    Readings of the same word whose only differences are one punctuation mark
    and one closing quote, each missing from some ("zijn’", "zijn."), give the
    word with both ("zijn.’"), unless a reading already has it.
    """
    parts = [_TRAILING.match(v).groups() for v in (ours, *versions)]
    if len({core for core, _, _ in parts}) != 1:
        return None
    marks = {m for _, m, _ in parts if m}
    quotes = {q for _, _, q in parts if q}
    if len(marks) != 1 or len(quotes) != 1:
        return None
    both = parts[0][0] + marks.pop() + quotes.pop()
    return None if both == ours or both in versions else both


def _decide(
    pdf_page, number, k, ours, a0, a1, others, box, lang, vision, reader, cache, around=("", ""),
    vouched: int | None = None,
) -> tuple[tuple[str, str | None, dict[str, str]], dict[str, float]]:  # fmt: skip
    """\"ours\", \"other\" with the chosen version, or \"review\", with each model's pick;
    and each model's confidence in it.

    The text model also reads the lines `around` this one (before, after), where a
    quote opens or a sentence goes on.

    Where the word list knows the words of one version only (`vouched`, an index
    into the versions), that version is recorded as its vote. It decides nothing:
    acting on it saved questions on the tuning books and added unasked errors on
    held-out ones.

    A pick is applied when both models make it and the vision model is at least
    somewhat sure, or, where the versions differ only in punctuation, dashes or
    spacing (which a text model can't judge), when the vision model alone is sure.
    Anything else goes to a human.
    """
    versions = [ours[a0:a1], *others]
    letters = "abcdefg"[: len(versions)]
    seen = _ask(
        vision,
        cache,
        {
            "page": number,
            "line": k,
            "readings": versions,
            "box": [round(v, 1) for v in box],
        },
        {
            "reading": ollaya.choice(
                "The image is cut from a scanned printed book. Which text does it show, "
                "letter for letter, including quote marks, dashes and punctuation?",
                {**{c: f"exactly “{v}”" for c, v in zip(letters, versions, strict=True)},
                 "neither": "something else"},
            )
        },
        image=lambda: _crop(pdf_page, box),
    )  # fmt: skip
    language = LANGUAGE_NAMES.get(lang, "")
    lines = [ours[:a0] + v + ours[a1:] for v in versions]
    intro = "Two OCR readings" if len(lines) == 2 else "Several OCR readings"
    read = _ask(
        reader,
        cache,
        {
            "line before": around[0],
            **dict(zip(letters, lines, strict=True)),
            "line after": around[1],
        },
        {
            "reading": ollaya.choice(
                f"{intro} of the same line of a printed {language} book differ. "
                "Which is the correct transcription, as printed, read between "
                "the line before and the line after?",
                {c: f"“{line}”" for c, line in zip(letters, lines, strict=True)},
            )
        },
    )
    pick = lambda value: versions[letters.index(value)] if value in letters else ""  # noqa: E731
    votes = {vision.model: pick(seen["value"]), reader.model: pick(read["value"])}
    confidence = {vision.model: seen["confidence"], reader.model: read["confidence"]}
    if vouched is not None:
        votes["word list"] = versions[vouched]
    return _choose(versions, letters, seen, read, votes), confidence


def _choose(versions, letters, seen, read, votes) -> tuple[str, str | None, dict[str, str]]:
    """The fixed rule: both models agreeing, or the vision model alone on typography."""
    if _typographic(versions) and seen["value"] in letters and seen["confidence"] >= SURE_ALONE:
        if seen["value"] == "a":
            return "ours", None, votes
        return "other", versions[letters.index(seen["value"])], votes
    if seen["value"] == read["value"] and seen["confidence"] >= SURE:
        if seen["value"] == "a":
            return "ours", None, votes
        return "other", versions[letters.index(seen["value"])], votes
    return "review", None, votes


def _typographic(versions: list[str]) -> bool:
    """Whether the versions have the same words, differing only in what lies between them.

    Joining two words ("have never" → "havenever", "ik ’s" → "ik's") changes the words.
    """
    words = lambda v: tuple(re.findall(r"\w+(?:'\w+)*", v.translate(_FOLD)))  # noqa: E731
    return len({words(v) for v in versions}) == 1


def _ask(client: OllayaClient, cache: DecisionCache, state: dict, questions: dict, image=None):
    key = DecisionCache.key(client.model, questions, state)
    answer = cache.get(key)
    if answer is None:
        a = client.decide(state, questions, image_png=image() if image else None)["reading"]
        answer = {"value": a.value, "confidence": a.confidence}
        cache.put(key, answer)
    return answer


def _crop(pdf_page: pymupdf.Page, box) -> bytes:
    clip = pymupdf.Rect(box) + (-CROP_PAD, -CROP_PAD, CROP_PAD, CROP_PAD)
    return pdf_page.get_pixmap(matrix=pymupdf.Matrix(CROP_ZOOM, CROP_ZOOM), clip=clip).tobytes(
        "png"
    )


def apply(pages: list[PageText], suspects: list[Suspect]) -> list[PageText]:
    """Copies of the pages with the chosen fixes, on lines still reading as the text layer did."""
    fixes: dict[tuple[int, str], list[Suspect]] = {}
    for s in suspects:
        if s.choice == "other":
            fixes.setdefault((s.page, s.original), []).append(s)
    out = []
    for page in pages:
        lines = []
        for line in page.lines:
            text = line.text
            # Right to left, so each fix leaves the spans before it in place.
            for s in sorted(fixes.get((page.number, text), []), key=lambda s: -s.start):
                text = text[: s.start] + s.chosen + text[s.end :]
            lines.append(replace(line, text=text) if text != line.text else line)
        out.append(replace(page, lines=lines))
    return out


def doubts(suspects: list[Suspect]) -> dict[tuple[int, str], list[tuple[str, list[str]]]]:
    """Per (page, line text), the readings of a line a human should choose between.

    Each reading is the whole line, the text layer's first, with the models that
    picked it.
    """
    out: dict[tuple[int, str], list[tuple[str, list[str]]]] = {}
    for s in suspects:
        if s.choice != "review":
            continue
        readings = out.setdefault((s.page, s.original), [(s.original, [])])
        for version in (s.ours, *s.others):
            line = s.original[: s.start] + version + s.original[s.end :]
            voters = [model for model, picked in s.votes.items() if picked == version]
            known = next((r for r in readings if r[0] == line), None)
            if known is None:
                readings.append((line, voters))
            else:
                known[1].extend(v for v in voters if v not in known[1])
    return out


def save(suspects: list[Suspect], path: Path) -> None:
    write_atomic(path, json.dumps([asdict(s) for s in suspects], ensure_ascii=False, indent=1))
