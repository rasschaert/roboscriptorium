"""Reflow's line-end hyphen decisions against the reference. No models.

For each body line ending in a hyphen, the aligned truth gives the printed word's head
and tail, and the reference's own vocabulary says whether the book prints the word
closed ("geluid") or with the hyphen ("wc-rol"); a break where it prints both, or
neither, isn't decidable and is skipped. `reflow.join` is then compared with that, and
so is each piece of evidence it could use:

- the rules in `reflow.join` (a capital after the break, a hyphen already in the word,
  the book printing the word with a hyphen elsewhere), how often each fires and is right;
- the word list (`lexicon.py`): where it knows exactly one of the two forms, its vote,
  crossed with reflow's call, so a vote that would fix a wrong call is told apart from
  one that would break a right one;
- a parts rule (closed form unknown, both parts known words → keep the hyphen), as a
  candidate question trigger: how often it fires and is right.

    uv run python experiments/probe_hyphen_breaks.py <book>[:pages[:chapters]] ...
    uv run python experiments/probe_hyphen_breaks.py goede-dochter--ia-scan:9-64:1-4 metro-2033--ia-scan:7-111:1-10
"""

import re
import sys
from collections import Counter
from pathlib import Path

from roboscriptorium import pdf, reflow
from roboscriptorium.book import Book
from roboscriptorium.cli import _verdicts
from roboscriptorium.disagreements import patch
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters, unmarked
from roboscriptorium.ir import SourceRef
from roboscriptorium.lexicon import Lexicon

_STRIP = re.compile(r"^[^\w]+|[^\w]+$")
_HYPHENS = ("-", "­", "¬")
_CLOSING = ".,;:!?’”'\""


def core(word: str) -> str:
    return _STRIP.sub("", word).lower()


def breaks(pages, truth, vocab):
    """Decidable line-end hyphen breaks: (page, line, line text, next line text, stem, rest,
    whether the print has the hyphen)."""
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
            if not stem or not rest:
                continue
            closed, hard = stem + rest, stem + "-" + rest
            if bool(vocab[closed]) == bool(vocab[hard]):
                continue
            yield p.number, i, text, lines[i + 1].text.strip(), stem, rest, bool(vocab[hard])


def made_hyphen(text: str, nxt: str, seen, known, stem: str, rest: str) -> bool:
    """Whether `reflow.join` keeps the hyphen at this break."""
    joined = reflow.join(text, nxt, seen, known)
    word = joined[len(text) - len(text.split()[-1]) :].split()[0]
    return core(word) == f"{stem}-{rest}"


grand: Counter = Counter()
grand_wrong = 0
grand_breaks = 0
for spec in sys.argv[1:]:
    name, pages_spec, chapters_spec = (spec.split(":") + ["", ""])[:3]
    folder = Path("work") / name
    book = Book.load(folder)
    first, last = book.body_pages
    if pages_spec:
        first, last = map(int, pages_spec.split("-"))
    layer = pdf.cached_text_layer(folder / "source.pdf", folder / "stages" / "textlayer.json")
    pages = [p for p in layer if first <= p.number <= last]
    reference = load_chapters(Golden.load(book.golden).text_dir)
    if chapters_spec:
        a, b = map(int, chapters_spec.split("-"))
        reference = reference[a - 1 : b]
    reference, _ = patch(reference, _verdicts(book))
    vocab = Counter(
        core(w) for ch in reference for par in ch.paragraphs for w in unmarked(par).split()
    )
    truth = align(pages, reference)
    seen = reflow.spellings(pages)
    lexicon = Lexicon.load("nld" if book.language == "nl" else "eng")

    tally: Counter = Counter()
    wrong = []
    n = 0
    for page, i, text, nxt, stem, rest, print_hyphen in breaks(pages, truth, vocab):
        n += 1
        closed, hard = stem + rest, f"{stem}-{rest}"
        made = made_hyphen(text, nxt, seen, lexicon.knows, stem, rest)
        right = made == print_hyphen
        tally["reflow right" if right else "reflow wrong"] += 1

        # The rules, as `reflow.join` applies them.
        first_word = nxt.split()[0] if nxt.split() else ""
        last_word = text.split()[-1][:-1]
        capital = not reflow._LOWER_START.match(nxt)
        all_caps = (
            capital
            and len(first_word.rstrip(_CLOSING)) > 1
            and first_word.rstrip(_CLOSING).isupper()
        )
        inner = "-" in last_word or "-" in first_word
        verdict = "right" if print_hyphen else "WRONG"
        if capital and not all_caps:
            tally[f"rule: capital after the break keeps the hyphen: {verdict}"] += 1
        if all_caps:
            tally[f"rule: all-caps word after the break keeps the hyphen: {verdict}"] += 1
        if inner and not capital:
            tally[f"rule: a hyphen already in the word keeps the hyphen: {verdict}"] += 1
        if not capital and not inner and seen[hard] > seen[closed]:
            tally[f"rule: the book prints it with a hyphen elsewhere: {verdict}"] += 1

        # The word list's vote, crossed with reflow's call.
        knows_closed, knows_hard = lexicon.knows(closed), lexicon.knows(hard)
        if knows_closed == knows_hard:
            vote = "silent"
        else:
            vote = "right" if knows_hard == print_hyphen else "WRONG"
        tally[f"word list {vote} where reflow is {'right' if right else 'wrong'}"] += 1

        # The parts rule as a question trigger.
        if vote == "silent" and not knows_closed and len(stem) >= 3 and len(rest) >= 3:
            if lexicon.knows(stem) and lexicon.knows(rest):
                tally[f"parts rule (closed unknown, both parts known → hyphen): {verdict}"] += 1

        if not right:
            pattern = (
                "all caps"
                if all_caps
                else "capital"
                if capital
                else "inner hyphen"
                if inner
                else "plain"
            )
            wrong.append(
                (
                    page,
                    i,
                    f"{last_word}-",
                    first_word,
                    hard if print_hyphen else closed,
                    pattern,
                    f"word list {vote}",
                )
            )

    pages_n = len(pages)
    print(
        f"\n== {name} pp. {first}-{last}: {n} decidable line-end hyphens ({n / max(1, pages_n):.1f}/page); "
        f"reflow wrong {tally['reflow wrong']} = {tally['reflow wrong'] / max(1, pages_n):.2f}/page"
    )
    for key in sorted(tally):
        if key.startswith(("rule", "word list", "parts")):
            print(f"   {tally[key]:4}  {key}")
    for w in wrong:
        print("   wrong: p%d:%d  %r + %r  print %r  (%s; %s)" % w)
    grand.update(tally)
    grand_wrong += tally["reflow wrong"]
    grand_breaks += n

print(f"\n== all: {grand_breaks} decidable breaks, reflow wrong {grand_wrong}")
for key in sorted(grand):
    if key.startswith(("rule", "word list", "parts")):
        print(f"   {grand[key]:4}  {key}")
