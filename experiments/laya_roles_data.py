"""Line-role rows for training a decision model, from the golden pairs' pages whose every
label is certain. No models (warm builds, as `sorterdata.lines` makes them).

A page is kept only when all of these hold:
- the reference text its body and heading lines hold continues the reference exactly
  where the previous kept line stopped (letters and digits only), so no text of the
  book went unplaced and every other line on it is certainly not text;
- each body or heading line holds as many words as it shows and reads close to them (OCR
  slips don't change a role; a line holding a neighbour's word was misaligned);
- each other line is a page number (digits or a Roman numeral), a running head (its text
  at the same edge of `RUNNING_PAGES` other pages) or marks without letters: a short line
  of dialogue the aligner gave away ("Ja.") or a footnote must not be taught as "other".
One failure drops the whole page.

    uv run python experiments/laya_roles_data.py [book …]

Writes work/probes/laya-roles/<book>.jsonl, one row per line of a kept page:
{"state", "questions", "gold", "book", "page", "line"}, and prints each book's share kept.
"""

import json
import re
import sys
from dataclasses import replace
from pathlib import Path

from rapidfuzz.distance import Levenshtein

from roboscriptorium import disagreements, pipeline, roles, typestyle
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring
from roboscriptorium.golden.align import align, unmarked
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.page import Repeats
from roboscriptorium.sorterdata import SPECS

OUT = Path("work/probes/laya-roles")
CLOSE = 0.8
RUNNING_PAGES = 2
NUMBER = re.compile(r"[\divxlcdm]+", re.IGNORECASE)
# Characters a resync may skip to find a line's text again before giving up on the book.
RESYNC_WINDOW = 20000
QUESTIONS = {
    "role": {
        "type": "choice",
        "instructions": "This is one line of text extracted from a scanned page of a printed "
        "book. What is it?",
        "criteria": {
            "body": "Part of the book's running text: prose, dialogue, a quotation or the "
            "short last line of a paragraph",
            "heading": "A heading of the book: a chapter, part or section title or number, "
            "set where it begins",
            "other": "Not the book's text: a page number, a running head, a library or "
            "digitisation stamp, a speck or a caption-free mark",
        },
    }
}


def letters(text: str) -> str:
    return re.sub(r"[\W_]", "", text.lower())


def fold(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.lower()))


def kept_pages(pages, labels, reference, repeats) -> set[int]:
    stream = "".join(
        letters(text)
        for ch in reference
        for text in [ch.heading] + [unmarked(p) for p in ch.paragraphs]
    )
    bad: set[int] = set()
    at, last = 0, None
    for page in pages:
        for k, line in enumerate(page.lines):
            lab = labels.get(roles.SourceRef(page.number, k))
            if lab is None:
                continue
            if lab.role == "other":
                bare = letters(line.text)
                furniture = (
                    not bare
                    or NUMBER.fullmatch(bare)
                    or repeats.other_pages(line.text, page.number, line.y0 / page.height)
                    >= RUNNING_PAGES
                )
                if not furniture:
                    bad.add(page.number)
                continue
            shown, held = fold(line.text), fold(lab.truth)
            if len(shown.split()) != len(held.split()) or (
                Levenshtein.normalized_similarity(shown, held) < CLOSE
            ):
                bad.add(page.number)
            t = letters(lab.truth)
            if not t:
                continue
            if stream.startswith(t, at):
                at += len(t)
            else:
                found = stream.find(t, at, at + RESYNC_WINDOW)
                bad.add(page.number)
                if last is not None:
                    bad.add(last)
                if found < 0:
                    return set()
                at = found + len(t)
            last = page.number
    return {p.number for p in pages} - bad


def style(styles, ref) -> str:
    s = styles.get(ref) if styles else None
    if s is None or s.size is None or s.weight is None:
        return "unknown"
    return f"size {s.size:.2f} and stroke weight {s.weight:.2f} of the body's"


def rows_of(spec: str) -> tuple[list[dict], int, int]:
    name, pages_arg, chapters = (spec.split(":") + ["", ""])[:3]
    book = Book.load(Path("work") / name)
    settings = replace(Settings.from_env(), sorter=False)
    stages = pipeline.run(
        book, pages=scoring.page_range(pages_arg or None), check_ocr=False, settings=settings
    )
    reference = load_chapters(Golden.load(book.golden).text_dir)
    if span := scoring.page_range(chapters or None):
        reference = reference[span[0] - 1 : span[1]]
    reference, _ = disagreements.patch(reference, scoring.verdicts(book))
    labels = align(stages.pages, reference)
    repeats = Repeats(stages.pages)
    keep = kept_pages(stages.pages, labels, reference, repeats)
    styles = typestyle.measure(book.source, stages.pages, book.stages / "type.json")
    rows = []
    for page in stages.pages:
        if page.number not in keep:
            continue
        for k in range(len(page.lines)):
            ref = roles.SourceRef(page.number, k)
            if ref not in labels:
                continue
            state = {**roles.state(page, k, repeats), "type": style(styles, ref)}
            rows.append(
                {"state": state, "questions": QUESTIONS, "gold": {"role": labels[ref].role},
                 "book": name, "page": page.number, "line": k}
            )  # fmt: skip
    return rows, len({r['page'] for r in rows}), len([p for p in stages.pages if p.lines])


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for spec in SPECS:
        name = spec.split(":")[0]
        if sys.argv[1:] and name not in sys.argv[1:]:
            continue
        rows, kept, total = rows_of(spec)
        (OUT / f"{name}.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
        )
        counts = {r: sum(x["gold"]["role"] == r for x in rows) for r in ("body", "heading", "other")}
        print(f"{name[:40]:40} pages kept {kept}/{total}  {counts}", flush=True)
