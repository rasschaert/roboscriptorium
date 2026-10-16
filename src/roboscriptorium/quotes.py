"""Places where a paragraph's quote marks don't pair up: a quote the OCR layer lost.

Curly quotes only: an opening ‘ or “ at a word's start, a closing ’ or ” at its
end. A ’ inside a word (zo’n, auto’s), opening a Dutch article (’s avonds, ’t) or
eliding letters (Flemish ’m, ’k; ’73) is an apostrophe. A quote left open at a
paragraph's end is asked about even when the next paragraph opens with the same mark:
a quotation running over paragraphs is rare (56 in ~58,000 golden paragraphs), a
closing mark lost at the end isn't. One left open right after a word ("zich ‘schrap
zette") is asked where it stands: a speck, or a term whose closing mark was lost beside
it.
Speech closed right after a letter at a paragraph's end has lost its stop: some books
kern it under the closing mark, and the layer misses it there.

A vision model's reading of such a line, told how the book is set (`style_prompt`),
proposes the line with its marks (`proposed`); the letters stay the text layer's.
"""

import re
from dataclasses import dataclass, replace

from rapidfuzz.distance import Levenshtein

from roboscriptorium.ir import Block, Paragraph, SourceRef
from roboscriptorium.typography import EllipsisStyle, guess_ellipsis

PAIRS = {"‘": "’", "“": "”"}
_ARTICLE = re.compile(r"’(s|t|n)\b")
# Flemish ’m (hem) and ’k (ik), and a year's two digits (’73), elided after a ’. Read as
# ‘ the mark is the layer's error, still asked about ("Ik zei ‘m dat…").
_ELIDED = re.compile(r"’(m|k|\d\d)\b")
_SENTENCE_BEFORE = re.compile(r"[.!?…]\s+$")
# A quoted term or title ("het ‘invoelend’", "‘Le mie prigioni’") runs to this many words
# inside a sentence; a longer quotation, or one that opens a sentence, is speech.
TERM_WORDS = 3


@dataclass(frozen=True)
class Place:
    sources: list[SourceRef]  # the paragraph's lines around the place
    why: str  # "no opening", "no closing" or "open at end"
    excerpt: str


def marks(text: str) -> list[tuple[int, str, str]]:
    """The quote marks in `text`: (offset, mark, "open" or "close"), apostrophes left out."""
    out = []
    for i, c in enumerate(text):
        if c not in "‘’“”'":
            continue
        if c == "'":
            # A straight quote among curly ones: its place says which way it faces.
            before = text[i - 1] if i else " "
            c = "‘" if before.isspace() or i == 0 else "’"
        before = text[i - 1] if i else " "
        after = text[i + 1] if i + 1 < len(text) else " "
        if c == "’" and before.isalnum() and after.isalnum():
            continue
        if c in "‘’" and not before.isalnum() and _ARTICLE.match("’" + text[i + 1 :]):
            continue
        if c == "’" and not before.isalnum() and _ELIDED.match(text, i):
            continue
        opening = before.isspace() or before in "(—–-[" or i == 0
        if c in "‘“" and opening:
            out.append((i, c, "open"))
        elif c in "’”" and not opening:
            out.append((i, c, "close"))
        elif c in "‘“":
            # An opening mark glued to the word before it: the layer lost a space.
            out.append((i, c, "open"))
        else:
            out.append((i, c, "close"))
    return out


def problems(text: str) -> list[tuple[int, str]]:
    """Offsets in `text` where a quote mark has no partner, and what is missing.

    Quotes nest in the same mark (‘Ik zei ‘arme kerel’ in het Hongaars!’), so an
    opening mark inside an open quote is a lost closing one only where it starts
    a new sentence.
    """
    found = []
    depth = dict.fromkeys(PAIRS, 0)
    # The offsets of the marks still open, innermost last.
    opened: dict[str, list[int]] = {c: [] for c in PAIRS}
    found_marks = marks(text)
    for k, (i, c, kind) in enumerate(found_marks):
        if kind == "open":
            if depth[c] and _SENTENCE_BEFORE.search(text, 0, i):
                found.append((i, "no closing"))
            else:
                depth[c] += 1
                opened[c].append(i)
            continue
        opener = next(o for o, cl in PAIRS.items() if cl == c)
        possessive = (
            c == "’" and text[i - 1 : i] in ("s", "z") and not text[i + 1 : i + 2].isalnum()
        )
        if possessive and depth[opener]:
            # A plural possessive inside a quotation (‘The animals’ language is hard,’) when
            # the marks after it pair up only if it doesn't close.
            later = [kd for _, m, kd in found_marks[k + 1 :] if m in "‘’"]
            left = depth[opener] + later.count("open") - later.count("close")
            possessive = left == 0
        if possessive:
            # A plural possessive (the animals’ language, Jezus’) needs no partner.
            continue
        if depth[opener]:
            depth[opener] -= 1
            opened[opener].pop()
        else:
            found.append((i, "no opening"))
    left = [i for offsets in opened.values() for i in offsets]
    # An open mark right after a word ("zich ‘schrap zette") is a speck or a term whose
    # close was lost beside it: asked where it stands, not at the paragraph's end.
    stray = [i for i in left if text[:i].rstrip()[-1:].isalpha()]
    found += [(i, "no closing") for i in stray]
    if len(stray) < len(left):
        found.append((len(text) - 1, "open at end"))
    elif stop := _unstopped(text, found_marks):
        found.append((stop, "no stop at end"))
    return sorted(found)


def _unstopped(text: str, found_marks: list[tuple[int, str, str]]) -> int | None:
    """The offset of a closing mark right after a letter at the paragraph's end, when it
    closes speech: printed speech ends on a stop, and some books kern it under the mark,
    where the layer loses it. None for a quoted term or title (`TERM_WORDS`)."""
    end = len(text.rstrip()) - 1
    if not found_marks or found_marks[-1][0] != end or found_marks[-1][2] != "close":
        return None
    if not text[end - 1 : end].isalpha():
        return None
    closing = found_marks[-1][1]
    opener = next(
        (i for i, c, kind in reversed(found_marks) if kind == "open" and PAIRS.get(c) == closing),
        None,
    )
    if opener is None:
        return None
    before = text[:opener].rstrip()
    inside_sentence = bool(before) and not before.endswith(tuple(".!?…:"))
    if inside_sentence and len(text[opener + 1 : end].split()) <= TERM_WORDS:
        return None
    return end


def unbalanced(paragraphs: list[Paragraph]) -> list[Place]:
    """Each place where a paragraph's quotes don't pair up, with the lines it falls on."""
    out = []
    for p in paragraphs:
        if not any(c in p.text for c in "‘’“”"):
            continue
        for offset, why in problems(p.text):
            out.append(Place(_around(p, offset, why), why, _excerpt(p.text, offset)))
    return out


def _around(p: Paragraph, offset: int, why: str) -> list[SourceRef]:
    """The lines a place falls on, by its share of the paragraph's text, one either side.

    A missing opening may sit anywhere before its closing mark, back to the paragraph's start.
    """
    n = len(p.sources)
    at = min(n - 1, offset * n // max(1, len(p.text)))
    first = 0 if why == "no opening" and at <= 2 else max(0, at - 1)
    return p.sources[first : min(n, at + 2)]


def _excerpt(text: str, offset: int) -> str:
    return text[max(0, offset - 40) : offset + 40].replace("\n", " ")


def _word_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    while end < len(text) and not text[end].isspace():
        end += 1
    return start, end


# A contraction's ending that an OCR layer split off by losing its apostrophe
# ("didn t", "I m", "auto s").
_SPLIT_CONTRACTION = re.compile(r"(?<=\w) (?=(?:t|m|s|re|ve|ll|d|n)\b)")


def _letters(text: str) -> list[str]:
    """Each word's letters and digits: what a proposal may not change."""
    return ["".join(c for c in word if c.isalnum()) for word in text.split()]


def proposed(ours: str, reading: str, ellipsis: str = "…") -> str:
    """`ours` with another reading's quote marks and punctuation.

    Each word where the two differ only in marks, not letters or word breaks (but for
    a contraction the layer split, "I m" for "I’m"), and the reading's has a quote
    mark, takes the reading's; every other word stays ours. The reading's straight
    quotes are taken as curly and its ellipses as the book's `ellipsis`."""
    reading = re.sub(r"(^|\s)'", r"\1‘", reading).replace("'", "’")
    reading = re.sub(r'(^|\s)"', r"\1“", reading).replace('"', "”")
    reading = re.sub(r"…|\.\.\.|\. \. \.", ellipsis, reading)
    spans: list[list[int]] = []
    for op in Levenshtein.opcodes(ours, reading):
        if op.tag == "equal":
            continue
        a = _word_span(ours, op.src_start, op.src_end)
        b = _word_span(reading, op.dest_start, op.dest_end)
        if spans and a[0] <= spans[-1][1]:
            last = spans[-1]
            spans[-1] = [last[0], max(last[1], a[1]), last[2], max(last[3], b[1])]
        else:
            spans.append([*a, *b])
    out, at = [], 0
    for a0, a1, b0, b1 in spans:
        theirs = reading[b0:b1]
        mine = ours[a0:a1]
        same = _letters(mine) == _letters(theirs)
        split = not same and _letters(_SPLIT_CONTRACTION.sub("’", mine)) == _letters(theirs)
        if (same or split) and any(c in theirs for c in CURLY):
            # A split contraction takes the reading's word; otherwise only its marks.
            out += [ours[at:a0], theirs if split else _marks(mine, theirs)]
            at = a1
    return "".join(out) + ours[at:]


CURLY = "‘’“”"
# What a proposal may take from a reading: quote marks and the punctuation beside them.
_MARKS = set(CURLY) | set(".,;:!?…")
_DASH = str.maketrans("-‐–—", "————")


def _marks(mine: str, theirs: str) -> str:
    """`mine` with the quote marks and punctuation where `theirs` differs; its letters,
    dashes and hyphens stay (Qwen reads "directeursk-’" where the print has "—’")."""
    out, at = [], 0
    # Dashes and hyphens count as one character, so a hyphen read for a dash is no edit.
    for op in Levenshtein.opcodes(mine.translate(_DASH), theirs.translate(_DASH)):
        if op.tag == "equal":
            continue
        gone, come = mine[op.src_start : op.src_end], theirs[op.dest_start : op.dest_end]
        moved = set(gone + come) & set(CURLY)
        # A quote may move across a space ("zei Charlie.’ Waarom", "Charlie. ‘Waarom").
        if set(gone + come) <= _MARKS | ({" "} if moved else set()):
            out += [mine[at : op.src_start], come]
            at = op.src_end
    return "".join(out) + mine[at:]


_LEAD = re.compile(f"^[{CURLY}]*")
_TRAIL = re.compile(f"[{CURLY}]*$")


def combined(ours: str, reading: str) -> str:
    """`ours` with the quote marks one reading has beyond the other's at a word's ends: a
    lost outer mark of a nested quotation ("worden.”" and "worden.’’" give "worden.”’")."""
    reading = re.sub(r"(^|\s)'", r"\1‘", reading).replace("'", "’")
    reading = re.sub(r'(^|\s)"', r"\1“", reading).replace('"', "”")
    words, theirs = ours.split(" "), reading.split()
    if [_letters(w) for w in words if _letters(w)] != [_letters(w) for w in theirs if _letters(w)]:
        return ours
    pairs = iter(t for t in theirs if _letters(t))
    out = []
    for w in words:
        if not _letters(w):
            out.append(w)
            continue
        t = next(pairs)
        a, b = _LEAD.match(w).group(), _LEAD.match(t).group()
        if len(b) > len(a):
            w = b[: len(b) - len(a)] + w
        a, b = _TRAIL.search(w).group(), _TRAIL.search(t).group()
        if len(b) > len(a):
            w = w + b[len(a) :]
        out.append(w)
    return " ".join(out)


# The kinds of reading a quote question offers beside the text layer's, in order.
KINDS = ("OCR check", "scan reading", "marks combined")


def readings(layer: str, checked: str, reading: str, ellipsis: str, single: bool) -> dict[str, str]:
    """A quote-flagged line's readings beside the layer's, by kind, each where it differs
    from those before it: the line as the OCR check left it (its fixed letters with the
    print's marks, which may be wrong in print too), with the marks the read model sees
    (`proposed`), and, for a nested quotation, those combined (`combined`, `nested`)."""
    out: dict[str, str] = {}
    seen = {layer}
    scan = proposed(checked, reading, ellipsis)
    both = combined(checked, scan)
    if single:
        both = nested(both)
    nesting = sum(both.count(m) for m in ("‘“", "”’")) > sum(checked.count(m) for m in ("‘“", "”’"))
    for kind, text in zip(KINDS, (checked, scan, both if nesting else checked), strict=True):
        if text not in seen:
            out[kind] = text
            seen.add(text)
    return out


def nested(text: str) -> str:
    """In a book whose dialogue opens with ‘, a doubled “ opens dialogue and a quotation in
    it at once (the layer reads ‘ as “ there), and a doubled ” closes both."""
    return re.sub("““", "‘“", re.sub("””", "”’", text))


def ellipsis(text: str, style: EllipsisStyle | None = None) -> str:
    """How the book prints an ellipsis: spaced dots where its style (book.toml's, else
    as the layer reads it) says so, else one character or three periods, by majority."""
    style = style or guess_ellipsis([text])
    if style is not None and style.dots == ". . .":
        return ". . ."
    return "…" if text.count("…") >= text.count("...") else "..."


def single_quoted_lines(texts: list[str]) -> bool:
    """Whether the book opens its dialogue with ‘ rather than “, counted on its lines."""
    text = " ".join(texts)
    return text.count("‘") > 2 * text.count("“")


def style_note(language: str, single: bool, ellipsis: str, dash: str | None) -> str:
    """How the book is set, as a sentence for a model reading or judging its text."""
    outer, inner = ("‘ ’", "“ ”") if single else ("“ ”", "‘ ’")
    marks = {"…": "the ellipsis as one character …", ". . .": "the ellipsis as spaced dots . . ."}
    marks = marks.get(ellipsis, "the ellipsis as ...")
    dashes = {"–": ", en dashes –", "—": ", em dashes —"}.get(dash or "", "")
    name = {"nl": "Dutch", "en": "English"}.get(language, language)
    return (
        f"This book is {name} and set in this style: dialogue in curly quotes {outer}, a "
        f"quotation inside dialogue in {inner}, the apostrophe ’, {marks}{dashes}."
    )


def style_prompt(language: str, single: bool, ellipsis: str, dash: str | None) -> str:
    """A prompt to transcribe one printed line, telling the model how the book is set."""
    return (
        style_note(language, single, ellipsis, dash)
        + " Use exactly these characters, never straight quotes. "
        "Transcribe the printed text in this image exactly as printed: every letter, accent, "
        "quote mark, dash and punctuation mark. It is one line of a book. Output only the text."
    )


# A straight ' opening a word that elides letters, not a quotation: Dutch ’s, ’t, ’n,
# Flemish ’m (hem) and ’k (ik), English ’em, ’tis, ’twas, ’cause, ’til, ’round, a decade
# (’60s).
ELISION = re.compile(r"'(?:[stnmk]|em|tis|twas|cause|til|round|\d\ds?)\b", re.IGNORECASE)
# What opens a quotation before it: the paragraph's start, a space, a bracket, a dash or
# another opening mark.
_OPENS_AFTER = "([{—–-‘“„"


def curl(blocks: list[Block]) -> list[Block]:
    """Copies of the paragraphs with straight quotes and apostrophes curled. A printed
    book sets curly ones; a straight one in the text is the text layer's. A double quote
    opens as the book's own opening mark does (“ or „, by majority)."""
    text = " ".join(b.text for b in blocks if isinstance(b, Paragraph))
    opening = "„" if text.count("„") > text.count("“") else "“"
    out = []
    for block in blocks:
        if isinstance(block, Paragraph) and ("'" in block.text or '"' in block.text):
            block = replace(block, text=curled(block.text, opening))
        out.append(block)
    return out


def curled(text: str, opening: str = "“") -> str:
    """`text` with its straight quotes curled by their place, letter for letter (so
    offsets and italics stay). Opening after a space, bracket, dash or opening mark;
    closing elsewhere; an apostrophe inside a word or eliding letters is ’. A mark right
    after a digit is a foot or an inch, and a mark with spaces on both sides says neither
    way: both stay straight."""
    chars = list(text)
    for i, c in enumerate(chars):
        if c not in "'\"":
            continue
        before = text[i - 1] if i else " "
        after = text[i + 1] if i + 1 < len(text) else " "
        if before.isdigit() or (before.isspace() and after.isspace()):
            continue
        # An opening mark is followed by its word: after a dash ("minderjarige –'") a
        # mark with nothing after it closes the speech the dash broke off.
        opens = (before.isspace() or before in _OPENS_AFTER) and not after.isspace()
        if c == '"':
            chars[i] = opening if opens else "”"
        elif opens and not ELISION.match(text, i):
            chars[i] = "‘"
        else:
            chars[i] = "’"
    return "".join(chars)
