"""Line-end hyphens the book and the word list leave undecided, asked of a decision model.

A hyphen at a line's end is the word's own ("half-cooked") or the break's ("halfcooked");
the print can't tell them apart, so `reflow.join` weighs the book's own spellings and
the word list first. Where neither says, English compounds go either way (34 of 77 in
the tuning books keep the hyphen) and the judge knows which: right on 63 where joining
was right on 43. Dutch ones almost always join (355 of 361), and the judge does no
better there, so it is asked about English only (`experiments/probe_hyphen_judge.py`).
"""

import json
from pathlib import Path

from roboscriptorium.clients.decide import choice
from roboscriptorium.files import write_atomic

VERSION = 1
LANGUAGES = {"en": "English"}


def asked(language: str) -> bool:
    """Whether a book in this language asks the judge about its undecided hyphens."""
    return language[:2] in LANGUAGES


class Compounds:
    """Whether an undecided line-end hyphen is the word's own, by the judge; its answers
    cached by the hyphenated word in `path`."""

    def __init__(self, client, model: str, language: str, path: Path):
        self._client, self._model, self._path = client, model, path
        self._language = LANGUAGES[language[:2]]
        self._answers: dict[str, float] = {}
        self._new = False
        if path.exists():
            blob = json.loads(path.read_text())
            if blob.get("version") == VERSION and blob.get("model") == model:
                self._answers = blob["answers"]

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
            blob = {"version": VERSION, "model": self._model, "answers": self._answers}
            write_atomic(self._path, json.dumps(blob, ensure_ascii=False, indent=1))
            self._new = False
