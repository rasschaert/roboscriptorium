"""Lines joined across their ends (`join`), and line-end hyphens: kept or dropped.

A hyphen at a line's end is the word's own ("half-cooked") or the break's ("halfcooked");
the print can't tell them apart, so `join` weighs the book's own spellings (`spellings`)
and the word list first, and asks a decision model about the ones they leave undecided
(`Compounds`). Where neither says, English compounds go either way (34 of 77 in
the tuning books keep the hyphen) and the judge knows which: right on 63 where joining
was right on 43. Dutch ones almost always join (355 of 361), and the judge does no
better there, so it is asked about English only (`experiments/probe_hyphen_judge.py`).
"""

import re
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from roboscriptorium.clients.decide import choice
from roboscriptorium.files import read_cache, write_cache
from roboscriptorium.pdf import PageText

VERSION = 1
LANGUAGES = {"en": "English"}
HYPHENS = ("-", "\u00ad", "\u00ac")
# Whether an undecided line-end hyphen is the word's own: (stem, rest, the text around the
# break, marked with |) → keep it.
Compound = Callable[[str, str, str], bool]
DASHES = ("\u2014", "\u2013")
# What isn't part of a word, for counting spellings ("thief-taker’s," → "thief-takers").
_WORD = re.compile(r"[^\w-]")
_BESIDE_END = re.compile(r"[\w'’-]*$")
_BESIDE_START = re.compile(r"[\w'’-]*")
# The words that open the second half of a word left open at a hyphen, its ending shared
# with a word further on: "in- en uitvoer", "zes- tot achtjarigen", "pre- and post-war".
_SUSPENDED_BY = frozenset({"en", "of", "noch", "tot", "and", "or", "nor"})


def asked(language: str) -> bool:
    """Whether a book in this language asks the judge about its undecided hyphens."""
    return language[:2] in LANGUAGES


class Compounds:
    """Whether an undecided line-end hyphen is the word's own, by the judge; its answers
    cached by the hyphenated word in `path`."""

    def __init__(self, client, model: str, language: str, path: Path):
        self._client, self._model, self._path = client, model, path
        self._language = LANGUAGES[language[:2]]
        blob = read_cache(path, VERSION, model=model)
        self._answers: dict[str, float] = blob["answers"] if blob else {}
        self._new = False

    def __call__(self, stem: str, rest: str, context: str) -> bool:
        """Whether `stem`-`rest`, broken at a line's end in `context` (the break marked
        with |), keeps its hyphen."""
        key = f"{stem}-{rest}".lower()
        if key not in self._answers:
            question = choice(
                f"A {self._language} book breaks a word across two lines with a hyphen at "
                "the line's end (shown as |). Is the hyphen part of the word's spelling, or "
                "only the line break's? Answer with how the word is spelled in running text.",
                {"closed": stem + rest, "hyphenated": f"{stem}-{rest}"},
            )
            state = {"language": self._language, "text": context}
            answer = self._client.decide(state, {"spelling": question}, model=self._model)
            self._answers[key] = answer["spelling"].probabilities.get("hyphenated", 0.0)
            self._new = True
        return self._answers[key] >= 0.5

    def save(self) -> None:
        if self._new:
            write_cache(
                self._path, VERSION, {"answers": self._answers}, indent=1, model=self._model
            )
            self._new = False


def spellings(pages: list[PageText]) -> Counter:
    """How often the book prints each word where no line break decides its spelling: all
    but a line's last word cut by a hyphen and the next line's first word, its rest."""
    seen: Counter = Counter()
    for page in pages:
        cut = False
        for line in page.lines:
            words = line.text.split()
            whole = words[1:] if cut else words
            cut = bool(words) and words[-1].endswith(HYPHENS)
            for word in whole[:-1] if cut else whole:
                if key := _WORD.sub("", word).lower():
                    seen[key] += 1
    return seen


def join(
    text: str,
    nxt: str,
    seen: Counter | None = None,
    known: Callable[[str], bool] | None = None,
    compound: Compound | None = None,
) -> str:
    """Append the next line, undoing hyphenation where the word continues.

    Whether a hyphen at the line's end is the word's own is settled by evidence, the
    strongest first: how the book spells the word inside lines (`seen`, from
    `spellings`: "thief-taker" elsewhere keeps it, "thieftaker" drops it); which of the
    two forms the language's word list knows (`known`, such as `Lexicon.knows`: it has
    "wc-rol" and not "wcrol"); a capital after the break ("Noord-Holland"; a word set
    in capitals isn't one); and, with a hyphen already in the word, whether the parts
    beside the break are both words ("Mens-erger-je-niet" keeps it) or one word broken
    ("Zuid-Lon-den" doesn't; without a word list the hyphen stays). Otherwise `compound`
    decides, a judge of the language (`hyphens.Compounds`), or else the hyphen was the
    break's.
    """
    if text.endswith(HYPHENS) and len(text) > 1 and text[-2].isalpha():
        last, first = text.split()[-1][:-1], nxt.split()[0] if nxt.split() else ""
        # The letters beside the break only: "pus—that's" continues "cam-" with "pus".
        stem = _WORD.sub("", _BESIDE_END.search(last).group())
        rest = _WORD.sub("", _BESIDE_START.match(first).group() or first)
        if _suspended(nxt, stem, rest, seen, known):
            return text.rstrip("".join(HYPHENS)) + "- " + nxt
        if _hyphen_stays(nxt, stem, rest, seen, known, compound, f"{text[-120:]}|{nxt}"):
            return text.rstrip("".join(HYPHENS)) + "-" + nxt
        return text[:-1] + nxt
    if text.endswith(DASHES):
        # A spaced dash ("ziet – hoe") keeps its spaces; a closed one ("alles—en") doesn't.
        return f"{text} {nxt}" if text[:-1].endswith(" ") else text + nxt
    if text.endswith("-") and len(text) > 1 and text[-2].isdigit() and nxt[:1].isdigit():
        return text + nxt  # a number range broken at the line's end ("1914-" / "1918")
    return f"{text} {nxt}"


def _suspended(
    nxt: str,
    stem: str,
    rest: str,
    seen: Counter | None,
    known: Callable[[str], bool] | None,
) -> bool:
    """Whether the hyphen leaves `stem` open before a conjunction ("voor-" / "en
    nadelen"), not breaking a word that happens to go on with one ("Toron-" / "to")."""
    words = nxt.split()
    if len(words) < 2 or words[0] not in _SUSPENDED_BY or rest != words[0]:
        return False
    closed = (stem + rest).lower()
    if seen and seen[closed]:
        return False
    return known is None or not known(stem + rest)


def _hyphen_stays(
    nxt: str,
    stem: str,
    rest: str,
    seen: Counter | None,
    known: Callable[[str], bool] | None,
    compound: Compound | None = None,
    context: str = "",
) -> bool:
    """Whether the hyphen between `stem` and `rest` is the word's own (see `join`)."""
    closed, hyphenated = stem + rest, f"{stem}-{rest}"
    if seen and seen[hyphenated.lower()] != seen[closed.lower()]:
        return seen[hyphenated.lower()] > seen[closed.lower()]
    if known is not None and known(hyphenated) != known(closed):
        return known(hyphenated)
    if not nxt[:1].islower():
        return not (len(rest) > 1 and rest.isupper())
    if "-" in stem or "-" in rest:
        if known is None:
            return True
        # The parts beside the break: a word of their own ("Lon" + "den") was broken
        # there; two words ("erger" + "je") were joined by the hyphen.
        before, after = stem.rsplit("-", 1)[-1], rest.split("-", 1)[0]
        if known(before + after):
            return False
        return min(len(before), len(after)) >= 3 and known(before) and known(after)
    return compound is not None and bool(stem) and bool(rest) and compound(stem, rest, context)
