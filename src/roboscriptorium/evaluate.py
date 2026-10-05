"""Score a built Document against its golden reference text.

Metrics:
- CER: character edits per reference character, after folding typography the
  EPUB is free to choose (quote and dash glyphs, word joiners, whitespace).
- WER: word edits per reference word, comparing lowercase letters and digits only,
  so it measures reading errors and ignores punctuation.
- Paragraph F1: whether paragraph breaks fall where the reference has them.

Chapter headings are left out of the reference text: until the pipeline marks
headings, it's the body text that is compared.
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

from rapidfuzz.distance import Levenshtein

from roboscriptorium.golden.reference import Chapter
from roboscriptorium.ir import Document

_FOLD = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "⁠": None,
        "﻿": None,
        " ": " ",
        "–": "—",
        "―": "—",
    }
)


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFC", text).translate(_FOLD)
    return re.sub(r"\s+", " ", text).strip()


def _bare_words(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


@dataclass
class Score:
    cer: float
    wer: float
    paragraph_precision: float
    paragraph_recall: float
    reference_words: int
    output_words: int
    confusions: list[tuple[str, str, int]] = field(default_factory=list)

    @property
    def paragraph_f1(self) -> float:
        p, r = self.paragraph_precision, self.paragraph_recall
        return 2 * p * r / (p + r) if p + r else 0.0


def _words_with_breaks(paragraphs: list[str]) -> tuple[list[str], set[int]]:
    """Words of all paragraphs, and the word indices that start a paragraph."""
    words, starts = [], set()
    for para in paragraphs:
        starts.add(len(words))
        words += normalise(para).split()
    return words, starts


def score(doc: Document, reference: list[Chapter], top: int = 25) -> Score:
    ref_words, ref_starts = _words_with_breaks([p for ch in reference for p in ch.paragraphs])
    out_words, out_starts = _words_with_breaks([b.text for b in doc.blocks])

    # Align on words, then count character edits inside the differing stretches.
    char_edits, confusions = 0, Counter()
    out_to_ref: dict[int, int] = {}
    for op in Levenshtein.opcodes(out_words, ref_words):
        if op.tag == "equal":
            for k in range(op.src_end - op.src_start):
                out_to_ref[op.src_start + k] = op.dest_start + k
            continue
        got = " ".join(out_words[op.src_start : op.src_end])
        want = " ".join(ref_words[op.dest_start : op.dest_end])
        char_edits += Levenshtein.distance(got, want) + (op.tag == "insert") + (op.tag == "delete")
        confusions[(got, want)] += 1
    ref_chars = sum(len(w) + 1 for w in ref_words)

    ref_bare = [w for p in reference for para in p.paragraphs for w in _bare_words(para)]
    out_bare = [w for b in doc.blocks for w in _bare_words(b.text)]
    word_edits = Levenshtein.distance(out_bare, ref_bare)

    # A break counts when it starts a word that aligns with a reference break.
    mapped = {out_to_ref[i] for i in out_starts if i in out_to_ref}
    hits = len(mapped & ref_starts)

    return Score(
        cer=char_edits / ref_chars,
        wer=word_edits / len(ref_bare),
        paragraph_precision=hits / len(out_starts) if out_starts else 0.0,
        paragraph_recall=hits / len(ref_starts),
        reference_words=len(ref_words),
        output_words=len(out_words),
        confusions=[(got, want, n) for (got, want), n in confusions.most_common(top)],
    )
