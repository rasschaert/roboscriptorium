"""A second scan of the same setting as a witness: where does its text layer disagree
with our build?

Aligns the built text (`stages/document.json`, or with --layer the book's own text layer,
to test the instrument) word by word with the other scan's text layer, and sorts each
disagreement by which side the word list knows:

- `ours-unknown`: our word isn't a word, the witness's is (likely our error);
- `theirs-unknown`: the witness's isn't (likely its OCR slip);
- `both-words`: both are words (an edition edit, or a real-word error on either side);
- `case`: the same letters in another case (small capitals, mostly);
- `other`: punctuation, numbers, neither side a word.

Writes every place to work/probes/second-scan/<book>.jsonl and prints counts and examples.

    uv run python experiments/probe_second_scan.py work/nervous-system work/nervous-system--scan2/source.pdf
"""

import argparse
import collections
import difflib
import json
import re
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from roboscriptorium.book import Book  # noqa: E402
from roboscriptorium.golden.manifest import Golden  # noqa: E402
from roboscriptorium.golden.reference import load_chapters  # noqa: E402
from roboscriptorium.lexicon import Lexicon  # noqa: E402

WORD = re.compile(r"[\w’'.,;:!?“”‘\"()—–-]+")
APOS = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def plain(token: str) -> str:
    """A token as compared: quotes and dashes folded, outer punctuation off."""
    return token.translate(APOS).strip("\"'.,;:!?()-")


def ours_from_document(book: Book) -> list[tuple[str, int]]:
    """The built text's words, each with the scan page its paragraph starts on."""
    doc = json.loads((book.stages / "document.json").read_text())
    out = []
    for block in doc["blocks"]:
        text = block.get("text") or ""
        page = block["sources"][0]["page"] if block.get("sources") else 0
        out += [(w, page) for w in text.split()]
    return out


def page_map(ours: Path, theirs: Path, first: int, last: int) -> dict[int, int]:
    """Each of our pages first..last to the other scan's page holding the same text: the
    best word match within a few pages of the last offset found, kept above 0.6."""
    a, b = pymupdf.open(ours), pymupdf.open(theirs)
    words = lambda doc, i: re.findall(r"[A-Za-z]{3,}", doc[i - 1].get_text())
    wb = {j: words(b, j) for j in range(1, len(b) + 1)}
    out: dict[int, int] = {}
    offset = None
    for p in range(first, last + 1):
        wa = words(a, p)
        if len(wa) < 20:
            continue
        near = range(1, len(b) + 1) if offset is None else range(p - offset - 8, p - offset + 9)
        scored = [
            (difflib.SequenceMatcher(None, wa, wb[j], autojunk=False).ratio(), j)
            for j in near
            if j in wb
        ]
        if not scored:
            continue
        r, j = max(scored)
        if r > 0.6:
            out[p], offset = j, p - j
    return out


def layer_words(pdf: Path, pages: dict[int, int], known) -> list[tuple[str, int]]:
    """A scan's text layer over the pages `pages` maps ours to (in our order), each word
    with our page; line-end hyphens joined where the joined word is known."""
    doc = pymupdf.open(pdf)
    out = []
    for p, q in sorted(pages.items()):
        lines = [ln.split() for ln in doc[q - 1].get_text().splitlines() if ln.strip()]
        words: list[str] = []
        for ln in lines:
            if words and words[-1].endswith("-") and ln and len(words[-1]) > 2:
                head = words[-1][:-1]
                joined = head + ln[0]
                if known(plain(joined).lower()):
                    words[-1] = joined
                    ln = ln[1:]
            words += ln
        out += [(w, p) for w in words]
    return out


def sort(a: list[str], b: list[str], known) -> str:
    pa, pb = [plain(w) for w in a], [plain(w) for w in b]
    if " ".join(pa).lower() == " ".join(pb).lower():
        return "case" if pa != pb else "other"
    ka = all(known(w.lower()) for w in pa if w) and any(pa)
    kb = all(known(w.lower()) for w in pb if w) and any(pb)
    if ka and kb:
        return "both-words"
    if kb and not ka and any(pa):
        return "ours-unknown"
    if ka and not kb and any(pb):
        return "theirs-unknown"
    return "other"


def wrong_words(ours: list[str], book: Book) -> set[int]:
    """Which of our words the golden reference doesn't have there (case ignored)."""
    ref = []
    for ch in load_chapters(Golden.load(book.golden).text_dir):
        for text in [ch.heading, *ch.paragraphs]:
            ref += [plain(w).lower() for w in text.split()]
    sm = difflib.SequenceMatcher(None, [w.lower() for w in ours], ref, autojunk=False)
    wrong = set()
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "equal":
            wrong |= set(range(i1, i2)) or {i1}
    return wrong


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("book", type=Path)
    ap.add_argument("witness", type=Path, help="the other scan's PDF")
    ap.add_argument("--layer", action="store_true", help="compare our text layer, not the build")
    ap.add_argument("--examples", type=int, default=15)
    ap.add_argument("--golden", action="store_true", help="label each place by the reference")
    args = ap.parse_args()

    book = Book.load(args.book)
    lex = Lexicon.load("eng" if book.language == "en" else "nld")
    known = lex.knows
    first, last = book.body_pages
    pages = page_map(book.source, args.witness, first, last)
    print(f"{len(pages)} of {last - first + 1} pages matched in the witness")
    ours = (
        layer_words(book.source, {p: p for p in pages}, known)
        if args.layer
        else ours_from_document(book)
    )
    theirs = layer_words(args.witness, pages, known)
    a = [plain(w) for w, _ in ours]
    b = [plain(w) for w, _ in theirs]
    sm = difflib.SequenceMatcher(None, [w.lower() for w in a], [w.lower() for w in b])
    places = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            # Case differences hide inside equal runs, since the match ignores case.
            for i, j in zip(range(i1, i2), range(j1, j2)):
                if a[i] != b[j]:
                    places.append(("case", i, i + 1, j, j + 1))
            continue
        if i2 - i1 > 8 or j2 - j1 > 8:
            places.append(("long", i1, i2, j1, j2))
            continue
        places.append((sort([w for w, _ in ours[i1:i2]], [w for w, _ in theirs[j1:j2]], known), i1, i2, j1, j2))

    wrong = wrong_words(a, book) if args.golden else set()
    out_dir = Path("work/probes/second-scan")
    out_dir.mkdir(parents=True, exist_ok=True)
    name = args.book.name + "--" + args.witness.stem + ("-layer" if args.layer else "")
    counts = collections.Counter(k for k, *_ in places)
    by_kind = collections.defaultdict(list)
    with (out_dir / f"{name}.jsonl").open("w") as f:
        for kind, i1, i2, j1, j2 in places:
            row = {
                "kind": kind,
                "page": ours[i1][1] if i1 < len(ours) else theirs[j1][1],
                "ours": " ".join(w for w, _ in ours[i1:i2]),
                "theirs": " ".join(w for w, _ in theirs[j1:j2]),
                "context": " ".join(w for w, _ in ours[max(0, i1 - 5) : i2 + 5]),
            }
            if args.golden:
                row["ours_wrong"] = bool(wrong & (set(range(i1, i2)) or {i1}))
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            by_kind[kind].append(row)
    print(f"{len(ours)} words ours, {len(theirs)} theirs; {len(places)} places")
    if args.golden:
        flagged = set()
        for _, i1, i2, *_ in places:
            flagged |= set(range(i1, i2)) or {i1}
        spans = _spans(sorted(wrong))
        hit = sum(1 for sp in spans if flagged & sp)
        print(f"our wrong places by the reference: {len(spans)}; flagged by the witness: {hit}")
    for kind, n in counts.most_common():
        bad = sum(1 for r in by_kind[kind] if r.get("ours_wrong"))
        print(f"\n## {kind}: {n}" + (f" (ours wrong at {bad})" if args.golden else ""))
        if kind == "long":
            continue
        for row in by_kind[kind][: args.examples]:
            mark = "  ✗" if row.get("ours_wrong") else "   "
            print(f"{mark}p{row['page']}: {row['ours']!r} | {row['theirs']!r}   … {row['context']}")


def _spans(idx: list[int]) -> list[set[int]]:
    """Runs of consecutive indices."""
    out: list[set[int]] = []
    for i in idx:
        if out and i - 1 in out[-1]:
            out[-1].add(i)
        else:
            out.append({i})
    return out


if __name__ == "__main__":
    main()
