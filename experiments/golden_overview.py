"""Overview of the golden books: what each costs and how golden its pair is. No models.

For every golden scan, over the pages its bench set scores (the whole body when it
isn't sliced): the set, body and scored pages, reference words and chapters, the
estimated cold cost (1.1 min per scored page, from docs/run-times.md), the text
layer against the reference (CER on body lines; the bare-word rate, which ignores
punctuation, so a gap between the two is typography; the share of lines the aligner
can't place; reference headings with a line on the scan), the manifest's declared
deviations, and the latest full eval's CER and WER. First-look books are left unmeasured.

    uv run python experiments/golden_overview.py > docs/golden-books.md
"""

import json
import tomllib
from dataclasses import astuple
from datetime import date
from pathlib import Path

from roboscriptorium import bench, pdf
from roboscriptorium.golden import signals
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters, unmarked

COLD_MINUTES_PER_PAGE = 1.1

specs = {}
for name, lst in bench.SETS.items():
    for s in lst:
        book, pages, chapters = (s.split(":") + ["", ""])[:3]
        specs.setdefault(book, (name, pages, chapters))


def latest_full_eval(book_dir: Path):
    path = book_dir / "eval-history.jsonl"
    if not path.exists():
        return None
    rows = [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]
    full = [r for r in rows if r.get("models") and r.get("ocr_check", True)]
    return full[-1] if full else None


# Manifest keys that undo a way the reference departs from its print.
DEVIATIONS = (
    "hyphen_dash", "capital_classes", "note_mark", "markup_spaces", "italics_unlike_print",
    "ellipsis_space",
)  # fmt: skip
faithful = []


def edition_verdicts(g: Golden, scan_id: str) -> int:
    """Verdicts that found the reference itself differing from the print."""
    path = g.data_root / "verdicts" / f"{scan_id}.jsonl"
    if not path.exists():
        return 0
    rows = [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]
    return sum(r.get("category") == "edition" for r in rows)


# Plain words for each departure a manifest undoes.
PLAIN = {
    "hyphen_dash": "dashes set as hyphens",
    "capital_classes": "small capitals written in lower case",
    "note_mark": "note marks numbered",
    "markup_spaces": "stray spaces in its markup",
    "italics_unlike_print": "italics unlike the print's",
    "ellipsis_space": "no space before an ellipsis",
}
USE = {"tuning": "tuning", "validation": "validation", "quick": "tuning", "reserve": "line roles only"}

details = []
for m in sorted(Path("golden").glob("*/manifest.toml")):
    g = Golden.load(m.parent.name)
    raw = tomllib.load(m.open("rb"))
    found = [k for k in DEVIATIONS if raw["reference"].get(k)]
    declared = ", ".join(found) or "none"
    for s in g.scans:
        key = f"{g.name}--{s.id}"
        role, pages, chapters = specs.get(key, ("reserve", "", ""))
        a, b = s.body_pages
        body = b - a + 1
        if pages:
            a, b = (int(x) for x in pages.split("-"))
        scored = b - a + 1
        book_dir = g.book_dir(s)
        ref = load_chapters(g.text_dir) if g.text_dir.exists() else []
        words = sum(len(unmarked(p).split()) for c in ref for p in c.paragraphs)
        if chapters:
            c0, c1 = (int(x) for x in chapters.split("-"))
            ref = ref[c0 - 1 : c1]
        cold = f"{COLD_MINUTES_PER_PAGE * scored / 60:.1f} h"
        ev = latest_full_eval(book_dir)
        ev_text = f"{ev['cer']:.2%} / {ev['wer']:.2%}" if ev else "none yet"
        title = raw.get("title", g.name)
        if key in bench.FIRST_LOOK:
            details.append(f"| {g.name} | **first look** | {body} / {scored} | {words} | {cold} | unmeasured | | | | {declared} | untouched |")
            faithful.append((None, title, "first look", 0, scored, found, s.id))
            continue
        if not (book_dir / "source.pdf").exists() or not ref:
            details.append(f"| {g.name} | {role} | {body} / {scored} | {words} | {cold} | no scan | | | | {declared} | {ev_text} |")
            continue
        layer = pdf.cached_text_layer(book_dir / "source.pdf", book_dir / "stages" / "textlayer.json")
        layer = [p for p in layer if a <= p.number <= b]
        cer, bare, unplaced, headings = astuple(signals.measure(layer, ref))
        details.append(
            f"| {g.name} | {role} | {body} / {scored} | {words} | {cold} | {cer:.2%} | {bare:.2%} |"
            f" {unplaced:.1%} | {headings} / {len(ref)} | {declared} | {ev_text} |"
        )
        faithful.append((bare, title, role, edition_verdicts(g, s.id), scored, found, s.id))


def differ(bare: float | None, scan_id: str) -> str:
    if bare is None:
        return "not looked at yet (its first look comes first)"
    return f"about 1 word in {round(1 / bare, -1):,.0f}" if bare else "never"


measured = sorted((f for f in faithful if f[0] is not None), key=lambda f: f[0])
waiting = [f for f in faithful if f[0] is None]

print(f"# Golden books\n\nGenerated by `experiments/golden_overview.py` on {date.today()}; don't edit by hand.")
print(
    "\nEach golden book is a scan of a printed book paired with the publisher's own text of"
    " that\nprinting. The build must turn the scan into that text, so a faithful pair is"
    " the\nmeasure of every change.\n"
)
if measured:
    best, worst = measured[:3], measured[-3:]
    print("**In short.** " + f"{len(measured)} scanned pairs are measured, {len(waiting)} wait for"
          " their first look. Most faithful: " + ", ".join(f[1] for f in best) + ". Least: "
          + ", ".join(f[1] for f in worst) + ". "
          "*Tuning* books are the ones choices are made on; *validation* books can only veto"
          " a change; a *first look* is scored once, untouched, before the book joins either.\n")  # fmt: skip
print("## How faithful each pair is\n")
print(
    "*Scan and text differ* compares the scan's own hidden text (one OCR program's reading)"
    " with\nthe publisher's text, word by word, punctuation aside. Most of the difference is"
    " that\nOCR's slips, so the most faithful pairs come out near the OCR's own rate, about"
    " 1 word in\n500 to 1,000. More than that means the publisher's text departs from the"
    " print\nsomewhere (a later edition, glued words). *Corrections* are places a person"
    " checked and\nfound the publisher's text, not the scan, was off; none can also mean"
    " nobody has checked\nyet.\n"
)
print("| Book | Used for | Scan and text differ | Corrections found | Known quirks of the text |")
print("| --- | --- | --- | --- | --- |")
for bare, title, role, editions, scored, found, scan_id in measured + waiting:
    quirks = ", ".join(PLAIN[k] for k in found) or "none known"
    use = USE.get(role, role)
    print(f"| {title} | {use} | {differ(bare, scan_id)} | {editions or '–'} | {quirks} |")
print(
    "\n## Details\n\nFor the scripts and agents. Per scan, over the pages its bench set scores."
    " *Cold* is the\nestimated cost of a run with nothing cached (1.1 min a page). *Layer CER*"
    " and *bare-word*\nare the text layer against the reference without any model; bare"
    " words ignore\npunctuation. *Unplaced* is the share of lines the aligner can't match"
    " (page furniture,\nspecks, text the reference lacks), over all lines. *Headings* counts"
    " reference headings\nwith a line on the scan. *Eval* is the latest full run, CER and WER.\n"
)
print("| Book | Set | Pages body / scored | Words | Cold | Layer CER | Bare-word | Unplaced | Headings | Declared | Eval CER / WER |")
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
for row in details:
    print(row)
