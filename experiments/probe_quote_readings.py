"""Probe: the quote questions' proposed readings (`Stages.quote_readings`) against the print.

For a golden scan's quote-flagged body lines, compares the line as the OCR check
leaves it and as proposed (the read model's marks on it, `quotes.proposed`) with
the aligned printed truth, dashes and ellipses folded. Counts where the proposal is
right and the line wrong (a fix the reviewer can pick), the reverse (a wrong offer),
and where there is no proposal.

    uv run python experiments/probe_quote_readings.py work/<book> [pages chapters] [--missed]
"""

import sys
from pathlib import Path

from roboscriptorium import disagreements, ocrcheck, pipeline
from roboscriptorium.book import Book
from roboscriptorium.cli import _range, _verdicts
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters

FOLD = str.maketrans({"–": "-", "—": "-", "¬": "-"})

args = [a for a in sys.argv if not a.startswith("--")]
book = Book.load(Path(args[1]))
pages_arg = args[2] if len(args) > 2 else None
chapters = _range(args[3]) if len(args) > 3 else None
stages = pipeline.run(book, pages=_range(pages_arg))
reference = load_chapters(Golden.load(book.golden).text_dir)
if chapters:
    reference = reference[chapters[0] - 1 : chapters[1]]
reference, _ = disagreements.patch(reference, _verdicts(book))
truth = align(stages.pages, reference)
lines = sorted(
    (r for r in stages.quote_lines if (t := truth.get(r)) and t.role == "body" and t.truth),
    key=lambda r: (r.page, r.line),
)
checked = {p.number: p for p in ocrcheck.apply(stages.pages, stages.suspects)}


def norm(text: str) -> str:
    return " ".join(text.translate(FOLD).replace("…", "...").split())


fixes = wrong_offers = useless = none = still_wrong = 0
for r in lines:
    line, want = checked[r.page].lines[r.line].text, truth[r].truth
    offer = stages.quote_readings.get(r)
    if offer is None:
        none += 1
        still_wrong += norm(line) != norm(want)
        continue
    lw, ow = norm(line) != norm(want), norm(offer) != norm(want)
    fixes += lw and not ow
    wrong_offers += ow and not lw
    useless += lw and ow
    if ow:
        print(f"p{r.page}:{r.line}\n  line     {line!r}\n  proposed {offer!r}\n  print    {want!r}")
print(
    f"\n{len(lines)} quote-flagged lines: {len(lines) - none} with a proposal: right where the "
    f"line is wrong {fixes}, wrong where it is right {wrong_offers}, both wrong {useless}; "
    f"no proposal {none} (of which the line is wrong {still_wrong})"
)

if "--missed" in sys.argv:
    read = __import__("json").loads((book.stages / "quote-readings.json").read_text())["lines"]
    for r in lines:
        line, want = checked[r.page].lines[r.line].text, truth[r].truth
        if r not in stages.quote_readings and norm(line) != norm(want):
            qwen = next((v for k, v in read.items() if k.startswith(f"{r.page}:{r.line}:")), None)
            print(f"missed p{r.page}:{r.line}\n  line  {line!r}\n  qwen  {qwen!r}\n  print {want!r}")
