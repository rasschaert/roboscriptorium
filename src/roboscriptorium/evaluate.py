"""Score a built Document against its golden reference text.

Metrics:
- CER: character edits per reference character, after folding typography the
  EPUB is free to choose (quote and dash glyphs, an ellipsis glyph or spaced
  dots, word joiners, soft hyphens, whitespace). `folded_reference` and `folded_output` count
  each kind on each side: what the fold forgave, so a pair whose EPUB and scan
  differ in convention shows it instead of hiding it.
- WER: word edits per reference word, comparing lowercase letters and digits only,
  so it measures reading errors and ignores punctuation.
- Paragraph F1: whether paragraph breaks fall where the reference has them.
- Headings: how many reference chapter headings the output has (matched in order,
  fuzzily), and how many output headings match none.
- Italics: precision and recall of italic words, over the words that align.

Headings are left out of the text comparison on both sides.
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

from roboscriptorium.golden.reference import Chapter
from roboscriptorium.ir import Document

_FOLD = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "„": '"',
        "\u2060": None,
        "\ufeff": None,
        "\u00ad": None,
        "–": "—",
        "―": "—",
        "…": "...",
    }
)
_SPACED_DOTS = re.compile(r"\.(?: \.){2,}")
# What `normalise` folds, by kind, for counting. Ellipses are counted first and taken
# out, so the spaces inside spaced dots count as the ellipsis.
_ELLIPSES = re.compile(r"…|\.(?:\s\.){2,}")
_FOLD_KINDS = {
    "quotes": re.compile("[‘’“”„]"),
    "dashes": re.compile("[–―]"),
    "spaces": re.compile("[\u2060\ufeff\u00a0\u202f\u2009]"),
    "soft hyphens": re.compile("\u00ad"),
}


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFC", text).translate(_FOLD)
    text = re.sub(r"\s+", " ", text)
    return _SPACED_DOTS.sub(lambda m: m.group(0).replace(" ", ""), text).strip()


def folds(texts: list[str]) -> dict[str, int]:
    """How often each kind of typography `normalise` folds occurs in `texts`."""
    out = {"ellipses": sum(len(_ELLIPSES.findall(t)) for t in texts)}
    rest = [_ELLIPSES.sub("", t) for t in texts]
    for kind, rx in _FOLD_KINDS.items():
        out[kind] = sum(len(rx.findall(t)) for t in rest)
    return out


def word_tokens(text: str) -> list[range] | None:
    """Per word of `normalise(text)`, the indices of the `text.split()` tokens it comes
    from (". . ." is three tokens and one word); None where they don't line up."""
    tokens = text.split()
    out, k = [], 0
    for word in normalise(text).split():
        start, joined = k, ""
        while k < len(tokens) and joined != word:
            joined += normalise(tokens[k])
            k += 1
            if not word.startswith(joined):
                return None
        if joined != word:
            return None
        out.append(range(start, k))
    while k < len(tokens) and not normalise(tokens[k]):
        k += 1
    return out if k == len(tokens) else None


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
    headings_found: int
    headings_expected: int
    headings_spurious: int
    italic_expected: int = 0
    italic_output: int = 0
    italic_precision: float = 0.0
    italic_recall: float = 0.0
    confusions: list[tuple[str, str, int]] = field(default_factory=list)
    # Per kind, how much typography the fold forgave on each side.
    folded_reference: dict[str, int] = field(default_factory=dict)
    folded_output: dict[str, int] = field(default_factory=dict)

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


def _italic_words(paragraphs: list[str], marks: list) -> set[int]:
    """Indices into `_words_with_breaks`' words of the italic ones.

    `marks` index each paragraph's `split()`; a word is italic when one of its tokens
    is (`word_tokens`). A paragraph whose tokens don't line up with its words is left out.
    """
    out, offset = set(), 0
    for para, italic in zip(paragraphs, marks, strict=True):
        groups = word_tokens(para)
        if groups is not None:
            out |= {offset + w for w, group in enumerate(groups) if any(k in italic for k in group)}
        offset += len(normalise(para).split())
    return out


def _heading_key(text: str) -> str:
    """Letters and digits, upper case, accents dropped ("Één" is "EEN")."""
    decomposed = unicodedata.normalize("NFKD", normalise(text).upper())
    return "".join(c for c in decomposed if c.isalnum())


_ROMAN = re.compile(r"M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})")
# Letters a layer reads for digits inside a number ("4I" for 41, "1O" for 10).
_LOOKALIKE_DIGITS = str.maketrans({"I": "1", "L": "1", "|": "1", "O": "0"})


def _numbers(text: str) -> tuple[list[str], str]:
    """The heading's chapter numbers, arabic or roman, with the layer's look-alikes folded
    ("CHAPTER 4I" holds "41", "CHAPTER IL" holds "II": an L where no numeral has one), and
    the key of the words around them ("CHAPTER")."""
    numbers, words = [], []
    for token in re.findall(r"[^\W_]+|\|", normalise(text).upper()):
        if any(c.isdigit() for c in token):
            numbers.append(token.translate(_LOOKALIKE_DIGITS))
        elif _ROMAN.fullmatch(token) or _ROMAN.fullmatch(token.replace("L", "I")):
            numbers.append(token if _ROMAN.fullmatch(token) else token.replace("L", "I"))
        else:
            words.append(token)
    return numbers, _heading_key(" ".join(words))


def _same_heading(
    a: str, b: str, numbered: tuple[tuple[list[str], str], tuple[list[str], str]] | None = None
) -> bool:
    if not a or not b:
        return False
    if a == b:
        return True
    if numbered and numbered[0][0] and numbered[1][0]:
        (na, wa), (nb, wb) = numbered
        if na != nb:
            return False  # "CHAPTER 2" isn't "CHAPTER 3", however alike the letters
        if wa == wb:
            return True  # the same number under the same words ("4I" is "41")
    short, long = sorted((a, b), key=len)
    # A heading split from its subtitle still counts ("THE FIRST CHAPTER" for
    # "THE FIRST CHAPTER PUDDLEBY"), but "I" is not "II".
    return fuzz.ratio(a, b) >= 85 or (len(short) >= 8 and long.startswith(short))


def match_headings(found: list[str], expected: list[str]) -> int:
    """How many expected headings appear among the found ones.

    An order-preserving alignment that maximises total similarity, so a missing
    "CHAPTER XXV." doesn't take "CHAPTER XXVI." and shift every later match.
    """
    fk = [_heading_key(t) for t in found]
    ek = [_heading_key(t) for t in expected]
    fn = [_numbers(t) for t in found]
    en = [_numbers(t) for t in expected]
    # best[i][j]: (similarity, matches) aligning found[:i] with expected[:j]
    best = [[(0.0, 0)] * (len(ek) + 1) for _ in range(len(fk) + 1)]
    for i in range(1, len(fk) + 1):
        for j in range(1, len(ek) + 1):
            options = [best[i - 1][j], best[i][j - 1]]
            if _same_heading(fk[i - 1], ek[j - 1], (fn[i - 1], en[j - 1])):
                sim, n = best[i - 1][j - 1]
                options.append((sim + fuzz.ratio(fk[i - 1], ek[j - 1]) / 100, n + 1))
            best[i][j] = max(options)
    return best[-1][-1][1]


def score(doc: Document, reference: list[Chapter], top: int = 25) -> Score:
    ref_words, ref_starts = _words_with_breaks([p for ch in reference for p in ch.paragraphs])
    if not ref_words:
        raise ValueError("the reference has no text")
    out_words, out_starts = _words_with_breaks([b.text for b in doc.paragraphs])

    # Align on words, then count character edits inside the differing stretches.
    char_edits, confusions = 0, Counter()
    out_to_ref: dict[int, int] = {}
    ops = Levenshtein.opcodes(out_words, ref_words)
    i = 0
    while i < len(ops):
        op = ops[i]
        if op.tag == "equal":
            for k in range(op.src_end - op.src_start):
                out_to_ref[op.src_start + k] = op.dest_start + k
            i += 1
            continue
        # Consecutive edits are one differing stretch: a word split in two comes back as
        # an insert beside a replace, and charged apart they cost ten letters' worth.
        s0, d0, s1, d1 = op.src_start, op.dest_start, op.src_end, op.dest_end
        while i + 1 < len(ops) and ops[i + 1].tag != "equal":
            i += 1
            s1, d1 = ops[i].src_end, ops[i].dest_end
        got = " ".join(out_words[s0:s1])
        want = " ".join(ref_words[d0:d1])
        char_edits += Levenshtein.distance(got, want) + (s0 == s1) + (d0 == d1)
        confusions[(got, want)] += 1
        i += 1
    ref_chars = sum(len(w) + 1 for w in ref_words)
    matched = match_headings([h.text for h in doc.headings], [ch.heading for ch in reference])

    ref_paragraphs = [p for ch in reference for p in ch.paragraphs]
    ref_marks = [
        ch.italic[k] if k < len(ch.italic) else ()
        for ch in reference
        for k in range(len(ch.paragraphs))
    ]
    ref_italic = _italic_words(ref_paragraphs, ref_marks)
    out_italic = _italic_words([b.text for b in doc.paragraphs], [b.italic for b in doc.paragraphs])
    hit_italic = {out_to_ref[i] for i in out_italic if i in out_to_ref} & ref_italic

    ref_bare = [w for p in reference for para in p.paragraphs for w in _bare_words(para)]
    out_bare = [w for b in doc.paragraphs for w in _bare_words(b.text)]
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
        headings_found=matched,
        headings_expected=len(reference),
        headings_spurious=len(doc.headings) - matched,
        italic_expected=len(ref_italic),
        italic_output=len(out_italic),
        italic_precision=len(hit_italic) / len(out_italic) if out_italic else 0.0,
        italic_recall=len(hit_italic) / len(ref_italic) if ref_italic else 0.0,
        confusions=[(got, want, n) for (got, want), n in confusions.most_common(top)],
        folded_reference=folds(ref_paragraphs),
        folded_output=folds([b.text for b in doc.paragraphs]),
    )
