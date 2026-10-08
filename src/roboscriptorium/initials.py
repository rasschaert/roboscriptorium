"""Guess which letter a decorated initial shows, for the reviewer to confirm.

A drawn initial leaves its word without a first letter ("NCE upon a time").
Only a few letters make that a word, and the book's own vocabulary (plus the
system word list for English) says which; the role model then picks among them
from the drawing.
"""

import re
import string
from pathlib import Path

from roboscriptorium.clients import decide
from roboscriptorium.clients.decide import DecisionClient
from roboscriptorium.pdf import PageText

WORD_LIST = Path("/usr/share/dict/words")


def vocabulary(pages: list[PageText], language: str) -> set[str]:
    words = set()
    if language.lower().startswith("en") and WORD_LIST.exists():
        words = {w.lower() for w in WORD_LIST.read_text().split()}
    for page in pages:
        for line in page.lines:
            words.update(w.lower() for w in re.findall(r"[^\W\d_]+", line.text))
    return words


def fragment(text: str) -> str:
    """The letters left of the word the initial begins: "NCE" from "NCE upon"."""
    first = text.split()[0] if text.split() else ""
    return re.match(r"[^\W\d_]*", first.split("-")[0]).group(0)


def candidates(rest: str, vocab: set[str]) -> list[str]:
    return [c for c in string.ascii_uppercase if (c + rest).lower() in vocab]


def guess(client: DecisionClient, vocab: set[str], png: bytes, line: str) -> str:
    """The letter, or "" when no letter makes the line's first word a word."""
    rest = fragment(line)
    letters = candidates(rest, vocab) if rest else []
    return choose(client, png, rest, letters) if letters else ""


def choose(client: DecisionClient, png: bytes, rest: str, letters: list[str]) -> str:
    if len(letters) == 1:
        return letters[0]
    question = {
        "letter": decide.choice(
            "The image is a decorated initial letter from a printed book. The word it "
            f"begins continues with “{rest}”. Which letter does the drawing show?",
            {c: f"The letter {c}, making “{c}{rest}”" for c in letters},
        )
    }
    return client.decide({"word_without_initial": rest}, question, image_png=png)["letter"].value
