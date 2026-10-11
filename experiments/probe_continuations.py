"""Lines the line roles drop or make headings that read as running text: they continue
a sentence the text before them left open, or open with a quotation mark. Scored against
the aligned reference on every tuning book (warm caches, no model calls).

    uv run python experiments/probe_continuations.py
"""

import re
from collections import Counter
from pathlib import Path

from roboscriptorium import bench, disagreements, ocr, pipeline
from roboscriptorium import page as P
from roboscriptorium.book import Book
from roboscriptorium.cli import _range, _verdicts
from roboscriptorium.config import Settings
from roboscriptorium.flags import treatment
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.ir import SourceRef
from roboscriptorium.lexicon import Lexicon

ENDS = re.compile(r"[.!?…:;][’'”\"»)]*$|[’”»]$")
OPENS = ("‘", "“", "„", "«")
LETTERS = re.compile(r"[^\W\d_]")


def candidate(text: str, known) -> bool:
    words = [re.sub(r"[^\w'’-]", "", w) for w in text.split()]
    tokens = text.split()
    if sum(len(LETTERS.findall(t)) for t in tokens) < 3 * len(tokens):
        return False
    words = [w for w in words if len(LETTERS.findall(w)) >= 2]
    if not (len(words) >= 2 or (words and len(LETTERS.findall(words[0])) >= 5)):
        return False
    return sum(map(known, words)) * 2 >= len(words)


score = {"continues": Counter(), "opens": Counter()}
for spec in bench.SETS["tuning"]:
    name, pages, chapters = (spec.split(":") + ["", ""])[:3]
    book = Book.load(Path("work") / name)
    st = pipeline.run(book, pages=_range(pages or None), settings=bench.unseen(Settings.from_env(), name))
    reference = load_chapters(Golden.load(book.golden).text_dir)
    if span := _range(chapters or None):
        reference = reference[span[0] - 1 : span[1]]
    reference, _ = disagreements.patch(reference, _verdicts(book))
    labels = align(st.pages, reference)
    known = Lexicon.load(ocr.language(book.language)).knows
    repeats = P.Repeats(st.pages)
    last_text = ""
    for page in st.pages:
        for i, line in enumerate(page.lines):
            ref = SourceRef(page.number, i)
            kind = treatment(st.model_roles.get(ref))
            if kind == "text":
                last_text = line.text.strip()
                continue
            text = line.text.strip()
            if kind != "dropped" or not candidate(text, known) or P.garbled(line):
                continue
            if repeats.other_pages(text, page.number):
                continue
            truth = labels[ref].role if ref in labels else "?"
            for rule, fires in (
                ("continues", bool(last_text) and not ENDS.search(last_text)),
                ("opens", text.startswith(OPENS)),
            ):
                if fires:
                    score[rule][(kind, truth)] += 1
                    if True:
                        print(f"  {rule:9} {truth:5} {name[:14]} p{page.number} l{i} {kind}: {text[:60]!r} after {last_text[-30:]!r}")
for rule, s in score.items():
    print(rule, dict(s))
