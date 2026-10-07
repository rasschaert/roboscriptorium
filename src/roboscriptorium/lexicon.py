"""A language's word list, and which of several readings of a span it can vouch for.

The words are the dictionary inside tesseract's own model for the language
(its LSTM word DAWG), unpacked once with `combine_tessdata` and
`dawg2wordlist` into work/lexicon/.
"""

import re
import subprocess
import tempfile
import unicodedata
from pathlib import Path

from roboscriptorium.files import write_atomic
from roboscriptorium.ocr import TESSDATA

CACHE = Path("work/lexicon")
HOMEBREW_TESSDATA = Path("/opt/homebrew/share/tessdata")
# A trailing hyphen only where the line ends: a word cut there.
_TOKEN = re.compile(r"\w+(?:[-’']\w+)*(?:-$)?")
_STRAIGHT = str.maketrans("‘’“”", "''\"\"")
_VOWEL = re.compile(r"[aeiouyàáâäèéêëìíîïòóôöùúûü]")
# Shorter words are too often both a word and a misreading ("Si" for "Sjjj").
MIN_LETTERS = 3


class Lexicon:
    def __init__(self, words: set[str]):
        self.words = words

    @classmethod
    def load(cls, lang: str) -> "Lexicon":
        path = CACHE / f"{lang}-words.txt"
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            write_atomic(path, "\n".join(sorted(_unpack(lang))))
        return cls(set(path.read_text().split()))

    def knows(self, word: str) -> bool:
        """Whether the word is in the list, as written, lowercase or capitalised.

        Acute accents on a known word set stress (míj, háár), so they don't make it unknown.
        """
        plain = _without_acutes(word)
        return any(w in self.words for v in (word, plain) for w in (v, v.lower(), v.capitalize()))

    def vouches(self, versions: list[str], continues: bool = False) -> int | None:
        """The one version whose words are all known, or None.

        A word cut by a line-end hyphen, and with `continues` the line's first word
        (the rest of the previous line's cut word), aren't judged. A version counts
        as known only with a known word of MIN_LETTERS or more. Versions that differ
        only in where words break aren't judged: a compound the list lacks
        ("martelkamers") splits into words it has.
        """
        if len({re.sub(r"\s", "", v.translate(_STRAIGHT)) for v in versions}) == 1:
            return None
        verdicts = [self._judge(v, continues) for v in versions]
        good = [i for i, v in enumerate(verdicts) if v is True]
        if len(good) == 1 and all(v is False for i, v in enumerate(verdicts) if i != good[0]):
            return good[0]
        return None

    def verdict(self, version: str, continues: bool = False) -> bool | None:
        return self._judge(version, continues)

    def _judge(self, version: str, continues: bool) -> bool | None:
        """True when every judged word is known, False when one isn't, None when none is judged."""
        tokens = _TOKEN.findall(version)
        if continues and tokens and version.lstrip()[:1].isalnum():
            tokens = tokens[1:]
        # The list holds junk ("rjg") and lacks interjections ("Sh"): a word without a
        # vowel isn't judged.
        judged = [
            t
            for t in tokens
            if not t.endswith("-") and not t.isdigit() and _VOWEL.search(t.lower())
        ]
        if any(not self.knows(t) for t in judged):
            return False
        if any(len(t) >= MIN_LETTERS for t in judged):
            return True
        return None


def _without_acutes(word: str) -> str:
    decomposed = unicodedata.normalize("NFD", word)
    return unicodedata.normalize("NFC", decomposed.replace("́", ""))


def _unpack(lang: str) -> set[str]:
    model = TESSDATA.get(lang, HOMEBREW_TESSDATA) / f"{lang}.traineddata"
    with tempfile.TemporaryDirectory() as tmp:
        prefix = f"{tmp}/{lang}."
        subprocess.run(
            ["combine_tessdata", "-u", str(model), prefix], check=True, capture_output=True
        )
        out = f"{tmp}/words.txt"
        subprocess.run(
            ["dawg2wordlist", prefix + "lstm-unicharset", prefix + "lstm-word-dawg", out],
            check=True,
            capture_output=True,
        )
        return set(Path(out).read_text().split())
