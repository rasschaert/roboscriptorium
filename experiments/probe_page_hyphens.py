"""Do the page readers know whether a line-end hyphen is the word's own? No models: the
page readings in the stage caches (`pagereader.py`).

For each decidable line-end hyphen (`probe_hyphen_breaks.breaks`: the reference prints
the word one way only), the word a page reading aligns to the layer's broken word is a
vote: hyphen kept or joined, counted only where the reader wrote the word whole on one
line (glm-ocr mostly keeps the print's line breaks, so its broken words say nothing).
Each vote is crossed with reflow's call: a vote that would fix a wrong call against one
that would break a right one.

    uv run python experiments/probe_page_hyphens.py <book>[:pages[:chapters]] ...
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

from rapidfuzz.distance import Levenshtein

from roboscriptorium import pagereader, pdf, reflow
from roboscriptorium.book import Book
from roboscriptorium.disagreements import patch
from roboscriptorium.golden import scoring
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters, unmarked
from roboscriptorium.ir import SourceRef
from roboscriptorium.lexicon import Lexicon

_STRIP = re.compile(r"^[^\w]+|[^\w]+$")
_HYPHENS = ("-", "­", "¬")


def core(word: str) -> str:
    return _STRIP.sub("", word).lower()


def breaks(pages, truth, vocab):
    for p in pages:
        lines = p.lines
        for i in range(len(lines) - 1):
            text = lines[i].text.rstrip()
            if not (text.endswith(_HYPHENS) and len(text) > 1 and text[-2].isalpha()):
                continue
            tr, tn = truth.get(SourceRef(p.number, i)), truth.get(SourceRef(p.number, i + 1))
            if not tr or not tn or tr.role != "body" or tn.role != "body":
                continue
            if not tr.truth.split() or not tn.truth.split():
                continue
            head, tail = tr.truth.split()[-1], tn.truth.split()[0]
            if not head.endswith("-"):
                continue
            stem, rest = core(head[:-1]), core(tail)
            if not stem or not rest or bool(vocab[stem + rest]) == bool(vocab[f"{stem}-{rest}"]):
                continue
            yield p, i, text, lines[i + 1].text.strip(), stem, rest, bool(vocab[f"{stem}-{rest}"])


def whole_words(page, reading: str) -> dict[int, str]:
    """Per line whose last word the layer breaks: the reading's word aligned to it, where
    the reading wrote it whole on one of its lines."""
    layer = pagereader._layer_words(page)
    words = pagereader.reading_words(reading)
    on_a_line = {w for line in reading.splitlines() for w in line.split()}
    ops = Levenshtein.opcodes(
        ["".join(pagereader._key(t) for _, t in pieces) for pieces in layer],
        [pagereader._key(w) for w, _ in words],
    )
    out = {}
    for op in ops:
        if op.tag != "equal":
            continue
        for d in range(op.src_end - op.src_start):
            pieces, (word, _) = layer[op.src_start + d], words[op.dest_start + d]
            if len(pieces) > 1 and word in on_a_line:
                out[pieces[0][0]] = word
    return out


tally: Counter = Counter()
for spec in sys.argv[1:]:
    name, pages_spec, chapters_spec = (spec.split(":") + ["", ""])[:3]
    folder = Path("work") / name
    book = Book.load(folder)
    first, last = map(int, pages_spec.split("-")) if pages_spec else book.body_pages
    layer = pdf.cached_text_layer(folder / "source.pdf", folder / "stages" / "textlayer.json")
    pages = [p for p in layer if first <= p.number <= last]
    reference = load_chapters(Golden.load(book.golden).text_dir)
    if chapters_spec:
        a, b = map(int, chapters_spec.split("-"))
        reference = reference[a - 1 : b]
    reference, _ = patch(reference, scoring.verdicts(book))
    vocab = Counter(core(w) for ch in reference for par in ch.paragraphs for w in unmarked(par).split())
    truth = align(pages, reference)
    seen = reflow.spellings(pages)
    lexicon = Lexicon.load("nld" if book.language == "nl" else "eng")
    readings = {}
    for reader in ("glm-page", "qwen-page"):
        cache = folder / "stages" / f"page-reading-{reader}.json"
        readings[reader] = json.loads(cache.read_text())["pages"] if cache.exists() else {}
    for page, i, text, nxt, stem, rest, printed in breaks(pages, truth, vocab):
        joined = reflow.join(text, nxt, seen, lexicon.knows)
        word = joined[len(text) - len(text.split()[-1]) :].split()[0]
        reflow_right = (core(word) == f"{stem}-{rest}") == printed
        votes = {}
        for reader, pages_read in readings.items():
            if str(page.number) not in pages_read:
                continue
            tally[reader, "page read"] += 1
            got = whole_words(page, pages_read[str(page.number)]).get(i)
            if got is None:
                continue
            keeps = "-" in core(got)
            votes[reader] = keeps
            verdict = "right" if keeps == printed else "WRONG"
            tally[reader, f"vote {verdict} where reflow is {'right' if reflow_right else 'wrong'}"] += 1
            if keeps != printed or not reflow_right:
                print(f"  {name[:20]} p{page.number}:{i} {stem}-{rest} print {'-' if printed else 'closed'}, reflow {'right' if reflow_right else 'wrong'}, {reader} {got!r}")
        if len(votes) == 2 and len(set(votes.values())) == 1:
            verdict = "right" if votes["qwen-page"] == printed else "WRONG"
            tally["both", f"agree {verdict} where reflow is {'right' if reflow_right else 'wrong'}"] += 1
        tally["all", f"reflow {'right' if reflow_right else 'wrong'}"] += 1

print()
for key in sorted(tally):
    print(f"  {tally[key]:5}  {key[0]:9} {key[1]}")
