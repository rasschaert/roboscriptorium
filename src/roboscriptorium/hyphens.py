"""Lines joined across their ends (`join`), and line-end hyphens: kept or dropped.

A hyphen at a line's end is the word's own ("half-cooked") or the break's ("halfcooked");
the print can't tell them apart, so `join` weighs the book's own spellings (`spellings`)
and the word list first, and asks a decision model about the ones they leave undecided
(`Compounds`). Where neither says, English compounds go either way (34 of 77 in
the tuning books keep the hyphen) and the judge knows which: right on 63 where joining
was right on 43. Dutch ones almost always join (355 of 361), and the judge does no
better there, so it is asked about English only (`experiments/probe_hyphen_judge.py`).
"""

import fcntl
import math
import pickle
import re
import tempfile
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from roboscriptorium.clients.decide import choice
from roboscriptorium.files import read_cache, write_cache
from roboscriptorium.pdf import PageText
from roboscriptorium.progress import Progress

# One process at a time asks the hyphen judges, machine-wide.
JUDGE_LOCK = Path(tempfile.gettempdir()) / "roboscriptorium-hyphen-judges.lock"

VERSION = 2
# A judge's answers are written to the cache after this many new ones.
SAVE_EVERY = 20
# The language a judge's question names.
NAMES = {"en": "English", "nl": "Dutch"}
LANGUAGES = {"en"}
# The languages a panel of judges (`Compounds` with several) is asked in.
PANEL_LANGUAGES = {"en", "nl"}
# In a Dutch book the learned decision keeps a hyphen only this sure, and only in a plain
# word (`Learned.plain`); elsewhere `vowel_clash` decides. Let loose it added hyphens the
# print lacks to names and foreign words (2026-11-18, docs/design.md).
DUTCH_CUT = 0.9
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
_DIAERESIS = {"e": "ë", "i": "ï", "o": "ö", "u": "ü"}
_SUSPENDED_BY = frozenset({"en", "of", "noch", "tot", "and", "or", "nor"})


# Two vowels a Dutch compound may not set side by side, read as one sound: its spelling
# puts a hyphen between the parts ("controle-experiment", "zee-eend", "auto-ongeluk").
_CLASH = frozenset(
    {"aa", "ae", "ai", "au", "ee", "ei", "eu", "ie", "ij", "oe", "oi", "oo", "ou", "ui", "uu"}
)


def vowel_clash(
    stem: str, rest: str, context: str = "", known: Callable[[str], bool] | None = None
) -> bool:
    """Whether a Dutch word broken at `stem`-`rest` keeps its hyphen because the vowels
    beside the break would be read as one sound joined ("woede-" / "uitbarsting",
    "mini-" / "jurk"): true by Dutch spelling for a compound, so only where `rest` is a
    word of four letters or more (`known`; the list holds suffixes such as "ers" and
    "ende" as words), and not after a diphthong's closing i, a glide that clashes with
    nothing ("vermoei-" / "ender", "sproei-" / "ende"). A word that isn't a compound
    takes a diaeresis there instead ("poëzie"), which `join` sets first where the word
    list knows it."""
    if len(stem) < 2 or len(rest) < 4 or (stem[-1] + rest[0]).lower() not in _CLASH:
        return False
    if stem[-1].lower() == "i" and stem[-2].lower() in "aeiou":
        return False
    return known is None or known(rest)


@dataclass(frozen=True)
class Signs:
    """What a book's own pages show of its hyphens, for a learned decision on a break they
    leave undecided (`features`): over every word but a line's last, how often it
    hyphenates (`habit`, hyphenated words in 10,000), which stems open and which rests
    close its hyphenated words, and how often each word stands alone."""

    english: bool
    habit: float
    opens: Counter = field(default_factory=Counter)
    closes: Counter = field(default_factory=Counter)
    alone: Counter = field(default_factory=Counter)


def book_signs(pages: list[PageText], language: str) -> Signs:
    """A book's `Signs`, from its pages as the text layer reads them (the build's `whole`)."""
    tokens = [
        _WORD.sub("", w).lower() for p in pages for ln in p.lines for w in ln.text.split()[:-1]
    ]
    alone = Counter(tokens)
    inline = [t for t in set(tokens) if "-" in t.strip("-")]
    return Signs(
        english=language[:2] == "en",
        habit=10_000 * sum(alone[t] for t in inline) / max(1, len(tokens)),
        opens=Counter(t.split("-")[0] for t in inline),
        closes=Counter(t.split("-")[-1] for t in inline),
        alone=alone,
    )


# The columns of `features`, in order; a learned decision adds each judge's chance.
FEATURES = (
    "english", "stem_length", "rest_length", "stem_known", "rest_known", "closed_known",
    "vowel_clash", "habit", "stem_opens", "rest_closes", "stem_alone", "rest_alone",
    "stem_ends_s", "stem_capital",
)  # fmt: skip


def features(
    stem: str, rest: str, signs: Signs, known: Callable[[str], bool] | None
) -> list[float]:
    """A break's `FEATURES` (`experiments/probe_hyphen_learned.py`)."""
    k = known or (lambda word: False)
    return [
        float(signs.english), len(stem), len(rest), float(k(stem)), float(k(rest)),
        float(k(stem + rest)), float(vowel_clash(stem, rest)), signs.habit,
        signs.opens[stem.lower()], signs.closes[rest.lower()],
        math.log1p(signs.alone[stem.lower()]), math.log1p(signs.alone[rest.lower()]),
        float(stem.lower().endswith("s")), float(stem[:1].isupper()),
    ]  # fmt: skip


@dataclass
class Learned:
    """A decision on an undecided break learned from the golden books' spellings
    (`experiments/train_hyphens.py`): the break's `features` and each judge's chance in
    `judges`' order, the hyphen kept at `cut` or more."""

    model: object
    judges: tuple[str, ...]
    cut: float
    signs: Signs
    known: Callable[[str], bool] | None = None

    def __call__(self, stem: str, rest: str, chances: dict[str, float]) -> float:
        x = features(stem, rest, self.signs, self.known) + [chances[j] for j in self.judges]
        return float(self.model.predict_proba([x])[0, 1])

    def plain(self, stem: str, rest: str) -> bool:
        """Whether the judges are asked about this break: in an English book always, in a
        Dutch one only where both parts are words of the list and the word starts in
        lower case (not a name or a foreign word)."""
        if self.signs.english:
            return True
        k = self.known or (lambda word: False)
        return stem[:1].islower() and k(stem) and k(rest)

    def keeps(self, stem: str, rest: str, chances: dict[str, float] | None) -> bool:
        """Whether the hyphen stays: by the judges' `chances` where the break is `plain`,
        and in a Dutch book where the vowels beside it clash (`vowel_clash`)."""
        if self.signs.english:
            return self(stem, rest, chances or {}) >= self.cut
        clash = vowel_clash(stem, rest, "", self.known)
        return clash or (chances is not None and self(stem, rest, chances) >= DUTCH_CUT)


def save_learned(path: Path, model: object, judges: tuple[str, ...], cut: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        pickle.dumps({"model": model, "judges": judges, "cut": cut, "features": FEATURES})
    )


def load_learned(path: Path, signs: Signs, known: Callable[[str], bool] | None = None) -> Learned:
    """The saved decision for a book of these `signs`; one made on other features stops."""
    saved = pickle.loads(path.read_bytes())
    if tuple(saved["features"]) != FEATURES:
        raise ValueError(f"{path} was trained on other features: train it again")
    return Learned(saved["model"], tuple(saved["judges"]), saved["cut"], signs, known)


def without(path: Path, book: str) -> Path:
    """Where the decision trained without `book` is kept, beside `path`."""
    return path.with_name(f"{path.stem}-without-{book}{path.suffix}")


def asked(language: str, panel: bool = False) -> bool:
    """Whether a book in this language asks the judge, or a `panel` of judges, about its
    undecided hyphens."""
    return language[:2] in (PANEL_LANGUAGES if panel else LANGUAGES)


class Compounds:
    """Whether an undecided line-end hyphen is the word's own, by the judge, or by the
    mean of the judges in `more` (each a client and its model) with it; the answers
    cached by the hyphenated word in `path`. `collect` gathers a book's questions first
    and asks them judge by judge, one book at a time on the machine, so each judge is
    loaded once a book; each judge's answers are kept as they come and stay (`partial` in
    the cache: a build stopped goes on from them, and a combination of the judges can be
    learned from them)."""

    def __init__(self, client, model: str, language: str, path: Path, more=(), learned=None):
        self._judges = [(client, model), *more]
        # A `Learned` decision in place of the judges' mean.
        self._learned = learned
        if learned is not None and set(learned.judges) - {m for _, m in self._judges}:
            raise ValueError(f"the learned hyphen decision needs the judges {learned.judges}")
        self._model, self._path = "+".join(m for _, m in self._judges), path
        self._language = NAMES[language[:2]]
        blob = read_cache(path, VERSION, model=self._model)
        self._answers: dict[str, float] = blob["answers"] if blob else {}
        self._partial: dict[str, dict[str, float]] = blob.get("partial", {}) if blob else {}
        self._pending: dict[str, tuple[str, str, str]] = {}
        self._collecting = False
        self._new = False

    def __call__(self, stem: str, rest: str, context: str) -> bool:
        """Whether `stem`-`rest`, broken at a line's end in `context` (the break marked
        with |), keeps its hyphen. While collecting, an unanswered word is noted and
        joined for now."""
        key = f"{stem}-{rest}".lower()
        if self._learned is not None and not self._learned.plain(stem, rest):
            return self._learned.keeps(stem, rest, None)
        if key not in self._answers or not self._heard(key):
            if self._collecting:
                self._pending.setdefault(key, (stem, rest, context))
                return False
            self._ask({key: (stem, rest, context)})
        if self._learned is not None:
            return self._learned.keeps(stem, rest, self._partial[key])
        return self._answers[key] >= 0.5

    def _heard(self, key: str) -> bool:
        """Whether every judge the decision needs has answered about `key`: the learned
        one needs each judge's chance, which a cache from before they were kept lacks."""
        if self._learned is None:
            return True
        return all(j in self._partial.get(key, {}) for j in self._learned.judges)

    def collect(self, run) -> None:
        """`run` (the reflows that will ask) gone through once for its questions, which
        are then asked judge by judge."""
        self._collecting = True
        try:
            run()
        finally:
            self._collecting = False
        pending, self._pending = self._pending, {}
        if pending:
            self._ask(pending)

    def _ask(self, questions: dict[str, tuple[str, str, str]]) -> None:
        """The questions put to each judge in turn, under the machine's lock for these
        judges: books built side by side would otherwise make Ollama swap judges at
        every question."""
        with open(JUDGE_LOCK, "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            for client, model in self._judges:
                asked = 0
                todo = sum(model not in self._partial.get(key, {}) for key in questions)
                progress = Progress(f"hyphen judge {model}", todo, "questions")
                for key, (stem, rest, context) in questions.items():
                    got = self._partial.setdefault(key, {})
                    if model in got:
                        continue
                    question = choice(
                        f"A {self._language} book breaks a word across two lines with a "
                        "hyphen at the line's end (shown as |). Is the hyphen part of the "
                        "word's spelling, or only the line break's? Answer with how the "
                        "word is spelled in running text.",
                        {"closed": stem + rest, "hyphenated": f"{stem}-{rest}"},
                    )
                    state = {"language": self._language, "text": context}
                    got[model] = client.decide(state, {"spelling": question}, model=model)[
                        "spelling"
                    ].probabilities.get("hyphenated", 0.0)
                    self._new = True
                    asked += 1
                    progress.add()
                    if asked % SAVE_EVERY == 0:
                        self.save()
                self.save()
        for key in questions:
            chances = [self._partial[key][model] for _, model in self._judges]
            self._answers[key] = sum(chances) / len(chances)
        self._new = True
        self.save()

    def save(self) -> None:
        if self._new:
            write_cache(
                self._path,
                VERSION,
                {"answers": self._answers, "partial": self._partial},
                indent=1,
                model=self._model,
            )
            self._new = False


def spellings(pages: list[PageText]) -> Counter:
    """How often the book prints each word where no line break decides its spelling: all
    but a line's last word cut by a hyphen and the next line's first word, its rest. A
    hyphenated chain also counts each pair of neighbouring parts ("in-de-toestand" counts
    "in-de" and "de-toestand"), which a break inside a chain is weighed by; a chain cut
    by the break counts its pairs away from the cut."""
    seen: Counter = Counter()
    for page in pages:
        cut = False
        for line in page.lines:
            words = line.text.split()
            rest, cut = cut, bool(words) and words[-1].endswith(HYPHENS)
            for k, word in enumerate(words):
                if not (key := _WORD.sub("", word).lower()):
                    continue
                head, tail = rest and k == 0, cut and k == len(words) - 1
                if not (head or tail):
                    seen[key] += 1
                parts = [p for p in key.split("-") if p]
                whole = len(parts) > 2 and not (head or tail)
                if whole or head or tail:
                    inner = parts[1 if head else 0 : len(parts) - 1 if tail else len(parts)]
                    for a, b in zip(inner, inner[1:], strict=False):
                        seen[f"{a}-{b}"] += 1
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
        if (marked := _diaeresis(stem, rest, known)) and nxt.startswith(rest):
            return text[:-1] + marked[len(stem) :] + nxt[len(rest) :]
        if _suspended(nxt, stem, rest, seen, known):
            return text.rstrip("".join(HYPHENS)) + "- " + nxt
        if _hyphen_stays(nxt, stem, rest, seen, known, compound, f"{text[:-1][-120:]}|{nxt}"):
            return text.rstrip("".join(HYPHENS)) + "-" + nxt
        return text[:-1] + nxt
    if text.endswith(DASHES):
        # A spaced dash ("ziet – hoe") keeps its spaces; a closed one ("alles—en") doesn't.
        return f"{text} {nxt}" if text[:-1].endswith(" ") else text + nxt
    if text.endswith("-") and len(text) > 1 and text[-2].isdigit() and nxt[:1].isdigit():
        return text + nxt  # a number range broken at the line's end ("1914-" / "1918")
    return f"{text} {nxt}"


def _diaeresis(stem: str, rest: str, known: Callable[[str], bool] | None) -> str:
    """The joined word with the diaeresis a Dutch break drops ("democratie-" / "en" →
    "democratieën"), when the list knows that form and not the plain one; else ''."""
    mark = _DIAERESIS.get(rest[:1])
    if known is None or not mark or known(stem + rest):
        return ""
    marked = stem + mark + rest[1:]
    return marked if known(marked) else ""


def _suspended(
    nxt: str,
    stem: str,
    rest: str,
    seen: Counter | None,
    known: Callable[[str], bool] | None,
) -> bool:
    """Whether the hyphen leaves `stem` open before a conjunction ("voor-" / "en
    nadelen"), not breaking a word that happens to go on with one ("Toron-" / "to").
    Where the closed form is a word too ("voor" + "en", "kinder" + "en"), the stem must
    join the end of the word after the conjunction ("voor- en achterkant": "voorkant";
    "kinder- en jeugdboeken": "kinderboeken")."""
    words = nxt.split()
    if len(words) < 2 or words[0] not in _SUSPENDED_BY or rest != words[0]:
        return False
    closed = (stem + rest).lower()
    if (seen and seen[closed]) or (known is not None and known(stem + rest)):
        return known is not None and _joins_end(stem, _WORD.sub("", words[1]), known)
    return True


def _joins_end(stem: str, word: str, known: Callable[[str], bool]) -> bool:
    """Whether `word` is a compound of two words of at least three letters whose end, joined
    to `stem`, makes a word too ("voor" with "achter|kant": "voorkant"). "tegen" is no
    compound, so "vij-" / "and tegen" isn't left open for "vijgen"."""
    return any(
        known(word[:k]) and known(word[k:]) and known(stem + word[k:])
        for k in range(3, len(word) - 2)
    )


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
    # An abbreviation in capitals before a word keeps its hyphen ("DNA-sporen",
    # "NSB-leden"); a word in capitals broken at the line's end goes on in capitals.
    if len(stem) > 1 and stem.isalpha() and stem.isupper():
        return True
    if "-" in stem or "-" in rest:
        # Within a chain, the book's spelling of the parts beside the break.
        before, after = stem.rsplit("-", 1)[-1].lower(), rest.split("-", 1)[0].lower()
        if seen and seen[f"{before}-{after}"] != seen[before + after]:
            return seen[f"{before}-{after}"] > seen[before + after]
        if known is None:
            return True
        # The parts beside the break: a word of their own ("Lon" + "den") was broken
        # there; two words ("erger" + "je", "second" + "to") were joined by the hyphen,
        # as was a sound said again ("doenk" + "doenk").
        before, after = stem.rsplit("-", 1)[-1], rest.split("-", 1)[0]
        if known(before + after):
            return False
        return before.lower() == after.lower() or (known(before) and known(after))
    return compound is not None and bool(stem) and bool(rest) and compound(stem, rest, context)
