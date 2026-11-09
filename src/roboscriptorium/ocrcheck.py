"""Check a scan's OCR text layer against more readings, line by line.

More readings of each body line: glm-ocr on the line's crop (best on letters
and words), tesseract on the page (best on dashes) and, told the book's style,
qwen3.8 on the crop (best on quote marks). Where any differs from the text layer
(widened to whole words), the judge (`judge_model`) picks a version from the crop of
the scan, and a text model (`check_model`) picks the version of the line that reads
right. Learned trust (`trust.py`) then fixes, keeps or asks; without it, the fixed rule
applies a pick both make with the judge at least somewhat sure, or the judge's alone on
a typographic difference, and leaves any other suspect to a human.

Fixes go into a copy of the pages, matched on the text layer's line text, so
the line texts the review keys its answers on stay as they are. Born-digital
PDFs, whose text is exact, aren't checked.
"""

import functools
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

import pymupdf
from rapidfuzz.distance import Levenshtein

from roboscriptorium import readers
from roboscriptorium.clients import decide
from roboscriptorium.clients.decide import DecisionClient
from roboscriptorium.files import write_atomic
from roboscriptorium.hyphens import HYPHENS
from roboscriptorium.ir import SourceRef
from roboscriptorium.lexicon import Lexicon
from roboscriptorium.pdf import LIGATURES, PageText, line_words, page_words, spells, spliced
from roboscriptorium.quotes import ELISION
from roboscriptorium.quotes import reading_curled as _curled
from roboscriptorium.roles import DecisionCache

# The fixed rule: the judge must be at least this sure, and agree with the text model.
SURE = 0.3
# Where versions differ only in punctuation, dashes or spacing, the text model can't
# tell them apart; the vision model decides alone when at least this sure.
SURE_ALONE = 0.5
CROP_ZOOM = 4
CROP_PAD = 4  # points around the suspect words
# A judge's answer on a crop is cached with the crop's settings. Answers cached without
# them were all made at this zoom and padding, and stand for that crop.
UNKEYED_CROP = {"zoom": 4, "pad": 4}
# A wide view (`<model>@wide`): this many points of the line either side of the suspect,
# and the question told so (judge set v2, 2026-11-07: pplx-decider 27B wrong on spaces
# 1.1% so, against 9.6% on the suspect alone).
WIDE = 40
WIDE_NOTE = (
    " The image shows a stretch of the line: the text in question stands in its middle, "
    "between the words around it."
)
# Curly quotes as straight ones, and a not sign (some OCR layers' line-end hyphen) as a
# hyphen, one character for one, so offsets stay put.
_FOLD = str.maketrans("‘’“”¬", "''\"\"-")
_OPENING_QUOTES = re.compile(r"(^|\s)([\"'‘’“”]+)")
# A dash as any reader sets it: an em or en dash, or a hyphen with a space before it (or
# opening a word-wide span, which starts after a space) and a space, a quote, a stop or
# comma, or the line's end after ("zag -, wat" is "zag —, wat").
_ANY_DASH = re.compile(r"\s*[—–]\s*|\s+-\s+|(?:\s+|^)-(?=['\",;:.!?]|$)")
# An ellipsis as a glyph, three dots or spaced dots, with or without a space before.
_ELLIPSIS = re.compile(r" ?(?:…|\. ?\. ?\.)")
_SPACE_BEFORE_APOSTROPHE = re.compile(r"(?<=\w) +'(?=\w)")
LANGUAGE_NAMES = {"nld": "Dutch", "eng": "English"}
# A word, a full stop and a lower-case word: an abbreviation mid-sentence ("bijv. de").
_ABBREVIATION = re.compile(r"(\w+)\.\s+[\"'‘’“”(]*([^\W\d_])")
# The first letter of a line, after any opening quotes, brackets or dashes.
_FIRST_LETTER = re.compile(r"[\"'‘’“”(—–-]*\s*([^\W\d_])")
# A doubled a, o or u with an accent on one letter only: stress is marked on both ("vóór").
# Not e, which French endings ("née") and a capital ("Eén") set so.
_HALF_ACCENT = re.compile(r"(?i)aá|áa|aà|àa|oó|óo|oò|òo|uú|úu")
# Marks prose doesn't print.
_GARBLED = re.compile(r"[~^|]")


@dataclass(frozen=True)
class Suspect:
    page: int
    line: int  # index into the page's lines, after missing lines were added
    original: str  # the line as the text layer reads it (glm-ocr's for an added line)
    start: int  # the differing words, as a span of `original`
    end: int
    ours: str
    others: tuple[str, ...]  # the other readings of the span
    box: tuple[float, float, float, float]
    choice: str  # "ours", "other" (then `chosen` says which), or "review"
    chosen: str | None = None
    # Each model's pick: a version of the span (`ours` or one of `others`), or "".
    votes: dict[str, str] = field(default_factory=dict)
    # Each model's confidence in its pick.
    confidence: dict[str, float] = field(default_factory=dict)
    # Per second reading, whether it reads each version (`ours` first) here.
    support: dict[str, tuple[bool, ...]] = field(default_factory=dict)
    # Per version, whether the word list knows all its words (None: it can't tell).
    known: tuple[bool | None, ...] = ()
    # Where the versions end the line and differ only in a break hyphen: the next
    # line's first word, which the place is read with ("dank-" + "baar").
    joined: str = ""
    # The judges' models by role: the vision judge, the text judge, then the second
    # vision judge where one was asked. Empty in suspects saved before it was recorded.
    judges: tuple[str, ...] = ()

    @property
    def judged_by(self) -> list[str]:
        """The judges' models by role (`judges`), else in the order their votes were
        recorded, which was that order."""
        return list(self.judges) or [m for m in self.votes if m != "word list"]

    @property
    def across(self) -> list[str]:
        """The versions as read across the line break (`joined`), or as they are."""
        return [across(v, self.joined) for v in (self.ours, *self.others)]

    @property
    def alternatives(self) -> list[str]:
        """The line as each other reading has it."""
        return [self.original[: self.start] + o + self.original[self.end :] for o in self.others]


def scanned(pdf: Path, sample: int = 10) -> bool:
    """Whether the PDF is a scan: its text is invisible OCR over page images, or it has no
    text at all (an image-only PDF, which `pdf.first_reading` reads). Not born-digital."""
    return _scanned(Path(pdf).resolve(), Path(pdf).stat().st_mtime_ns, sample)


@functools.cache
def _scanned(pdf: Path, mtime: int, sample: int) -> bool:
    invisible = visible = 0
    with pymupdf.open(pdf) as doc:
        step = max(1, doc.page_count // sample)
        for page in list(doc)[::step]:
            for span in page.get_texttrace():
                if span["type"] == 3:
                    invisible += len(span["chars"])
                else:
                    visible += len(span["chars"])
    return invisible > visible or visible == 0


def _word_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start > 0 and text[start - 1] != " ":
        start -= 1
    while end < len(text) and text[end] != " ":
        end += 1
    return start, end


def differences(ours: str, theirs: str) -> list[tuple[int, int, int, int]]:
    """Where two readings of a line differ, widened to whole words, as spans of each.

    Curly and straight quotes count as the same. A difference only in the kind of
    an opening quote isn't one: OCR models read a printed “ as ‘, and no model can
    tell them apart in a crop. A lost opening quote or apostrophe is. Nor is a
    reading without the space before an apostrophe ("uur’s" for "uur ’s"): OCR
    models miss the narrow space Dutch print sets before the article ’s, and no
    judge sees it in a crop. Nor are differences in a dash's kind or the space
    around it, or in how an ellipsis is set (…, ..., . . .): a book sets all its
    dashes and ellipses one way (`typography.py`).
    """
    spans = []
    for op in Levenshtein.opcodes(ours.translate(_FOLD), theirs.translate(_FOLD)):
        if op.tag == "equal":
            continue
        a = _word_span(ours, op.src_start, op.src_end)
        b = _word_span(theirs, op.dest_start, op.dest_end)
        if spans and a[0] <= spans[-1][1]:
            prev = spans.pop()
            a, b = (prev[0], max(prev[1], a[1])), (prev[2], max(prev[3], b[1]))
        spans.append((*a, *b))
    return [
        s
        for s in spans
        if _bare(ours[s[0] : s[1]]) != _bare(theirs[s[2] : s[3]])
        and ours[s[0] : s[1]].translate(_FOLD).strip()
        != theirs[s[2] : s[3]].translate(_FOLD).strip()
        and _SPACE_BEFORE_APOSTROPHE.sub("'", ours[s[0] : s[1]].translate(_FOLD))
        != theirs[s[2] : s[3]].translate(_FOLD)
        and _alike(ours[s[0] : s[1]]) != _alike(theirs[s[2] : s[3]])
    ]


def _alike(text: str) -> str:
    """Text with every dash between words and every ellipsis alike, quotes straight: the
    book's dash and ellipsis style are set book-wide (`typography.py`)."""
    return _ELLIPSIS.sub("…", _ANY_DASH.sub("—", text.translate(_FOLD))).strip()


def _bare(text: str) -> str:
    """Text with every opening quote alike: its kind is no difference, a lost one is.

    Each mark of a run folds on its own ("‘’t Is" keeps two), so a lost one is a
    difference there too."""
    return _OPENING_QUOTES.sub(lambda m: m[1] + "'" * len(m[2]), text.translate(_FOLD)).strip()


def _box(words: list, box, original: str, start: int, end: int):
    """The suspect words' box: the text layer's word boxes, or a share of the line's box.

    At the line's start or end it reaches one em further, where a mark the text
    layer missed is printed.
    """
    k0 = original[:start].count(" ")
    k1 = k0 + original[start:end].strip().count(" ") + 1
    x0, y0, x1, y1 = box
    if spells(words, original):
        out = list(readers._union(words[k0:k1]))
    else:
        out = [x0 + (x1 - x0) * start / len(original), y0, x0 + (x1 - x0) * end / len(original), y1]
    em = y1 - y0
    if start == 0:
        out[0] -= em
    if end == len(original):
        out[2] += em
    return tuple(out)


def check(
    pdf: Path,
    pages: list[PageText],
    readings: dict[str, dict[SourceRef, str]],
    lang: str,
    vision: DecisionClient | decide.HostedClient,
    reader: DecisionClient | None,
    cache: DecisionCache,
    lexicon: Lexicon | None = None,
    style: str = "",
    alarms=(),
    alarm_below: float = 1.0,
    lower_capitals: bool = False,
) -> list[Suspect]:
    """Suspects where any other reading (by name) differs from the text layer, each with a
    decision, and with `lower_capitals` where small capitals may have been read in lower
    case though no reading disputes it (`capitals_doubts`). `style` tells the vision
    judges how the book is set (`quotes.style_note`).
    `alarms`, second vision judges, are asked the vision judge's question where that
    judge is less sure than `alarm_below` (one with a `wide` view on the suspect with its
    line around it); each pick is a vote for the arbiter, not part of the fixed rule, and
    a suspect one wasn't asked about has no vote of it.

    The judges answer one at a time over the whole book, each into `cache`, before the
    pass that decides reads every answer back: the four don't fit in the GPU's memory
    together, and asked suspect by suspect they evicted each other on every call
    (Nervous System, 2026-11-09: 585 model loads an hour, 4–7 s each)."""
    args = (pdf, pages, readings, lang)
    rest = (cache, lexicon, style)
    judges = [m for m in (vision, reader, *alarms) if m is not None]
    for live in judges[:-1]:
        later = lambda m, live=live: m if m is None or m is live else _Later(m)  # noqa: E731
        _check(*args, later(vision), later(reader), *rest, tuple(map(later, alarms)), alarm_below)
    return _check(*args, vision, reader, *rest, alarms, alarm_below)


class _Later:
    """A judge whose turn hasn't come: it answers from the cache where it can, and
    otherwise with nothing, which is never cached (`_ask`)."""

    def __init__(self, client):
        self._client = client

    def __getattr__(self, name):
        return getattr(self._client, name)


def _check(
    pdf: Path,
    pages: list[PageText],
    readings: dict[str, dict[SourceRef, str]],
    lang: str,
    vision,
    reader,
    cache: DecisionCache,
    lexicon: Lexicon | None,
    style: str,
    alarms,
    alarm_below: float,
) -> list[Suspect]:
    """`check`'s pass over the book with the judges as given."""
    suspects = []
    curly = curly_book(pages)
    shortened = abbreviations(pages)
    counts = book_words(pages) if lower_capitals else Counter()
    with pymupdf.open(pdf) as doc:
        for page in pages:
            pdf_page = doc[page.number - 1]
            words = line_words(page_words(pdf_page, page), page)
            boxes = readers.line_boxes(pdf_page, page)
            for k, line in enumerate(page.lines):
                ours = line.text
                # A reader's ligature glyph spelled out: "ﬂed" and "fled" are one word.
                others = {
                    n: r.get(SourceRef(page.number, k), "").translate(LIGATURES)
                    for n, r in readings.items()
                }
                read = [o for o in others.values() if o]
                around = (
                    page.lines[k - 1].text if k > 0 else "",
                    page.lines[k + 1].text if k + 1 < len(page.lines) else "",
                )
                differences = merged_differences(ours, read, curly)
                if lower_capitals:
                    taken = [(d0, d1) for d0, d1, _ in differences]
                    differences += capitals_doubts(ours, taken, counts)
                for a0, a1, alternatives in differences:
                    disputed = [(d0, d1) for d0, d1, _ in differences if (d0, d1) != (a0, a1)]
                    alternatives = [
                        v
                        for v in alternatives
                        if not line_end_stop(ours, a0, a1, v, around[1], shortened, disputed)
                        and not half_accent(ours[a0:a1], v)
                        and not garbled(ours[a0:a1], v)
                        and not b_for_h(ours[a0:a1], v)
                        and not ij_misread(ours[a0:a1], v)
                        and not quote_misread(ours[a0:a1], v)
                    ]
                    if not alternatives:
                        continue
                    versions = [ours[a0:a1], *alternatives]
                    box = _box(words[k], boxes[k], ours, a0, a1)
                    continues = a0 == 0 and k > 0 and page.lines[k - 1].text.endswith(HYPHENS)
                    joined = hyphen_only(ours, a1, versions, around[1])
                    read_as = [across(v, joined) for v in versions]
                    (choice, chosen, votes), confidence = _decide(
                        pdf_page, page.number, k, ours, a0, a1, alternatives, box, lang,
                        vision, reader, cache, around,
                        lexicon.vouches(read_as, continues) if lexicon else None,
                        joined, style, alarms, alarm_below,
                    )  # fmt: skip
                    support = {
                        n: supports(ours, other, a0, a1, versions, curly)
                        for n, other in others.items()
                    }
                    known = known_versions(lexicon, read_as, continues) if lexicon else ()
                    suspects.append(
                        Suspect(
                            page.number,
                            k,
                            ours,
                            a0,
                            a1,
                            ours[a0:a1],
                            tuple(alternatives),
                            box,
                            choice,
                            chosen,
                            votes,
                            confidence,
                            support,
                            known,
                            joined,
                            tuple(m.model for m in (vision, reader, *alarms) if m is not None),
                        )  # fmt: skip
                    )
    return suspects


def abbreviations(pages: list[PageText]) -> set[str]:
    """The words the book prints with a full stop before a lower-case word, folded to
    lower case: its abbreviations ("bijv.", "blz.")."""
    return {
        m.group(1).lower()
        for page in pages
        for line in page.lines
        for m in _ABBREVIATION.finditer(line.text)
        if m.group(2).islower()
    }


def half_accent(ours: str, version: str) -> bool:
    """Whether `version` accents one letter of a doubled vowel (`_HALF_ACCENT`) where the
    layer doesn't: no spelling does, so it is never the print."""
    return bool(_HALF_ACCENT.search(version)) and not _HALF_ACCENT.search(ours)


def garbled(ours: str, version: str) -> bool:
    """Whether `version` brings in a mark prose doesn't print (`_GARBLED`) that the layer
    lacks."""
    return bool(_GARBLED.search(version)) and not _GARBLED.search(ours)


def b_for_h(ours: str, version: str) -> bool:
    """Whether `version` only reads one of the layer's h's as a b ("huis" → "buis", "hij"
    → "bij"): in the trust data never the print (0 of 91), where b read as h is now and
    then (17 of 45, the layer's own "bet" for "het")."""
    if len(ours) != len(version):
        return False
    diff = [(a, b) for a, b in zip(ours, version, strict=True) if a != b]
    return diff == [("h", "b")]


# What a reader makes of a printed "ij" ("dijk" → "duk", "duik", "dyk", "diik", "dik").
IJ_MISREADS = ("u", "ui", "y", "ii", "i")


def ij_misread(ours: str, version: str) -> bool:
    """Whether `version` only reads one of the layer's "ij"s as another letter or two
    (`IJ_MISREADS`): in the trust data never the print (0 of 68), where the other way,
    the layer's "Hy", "ziin" or "mi" for "Hij", "zijn" or "mij", it is half the time
    (45 of 89)."""
    at = ours.find("ij")
    while at >= 0:
        if any(ours[:at] + m + ours[at + 2 :] == version for m in IJ_MISREADS):
            return True
        at = ours.find("ij", at + 1)
    return False


# What follows an apostrophe joining two words in print: a contraction's end ("you’re",
# "didn’t", "zo’n", Flemish "’k"), a Dutch diminutive or plural ("baby’tje", "foto’s").
_JOINED_ENDS = {
    "s",
    "t",
    "m",
    "d",
    "n",
    "k",
    "r",
    "re",
    "ve",
    "ll",
    "em",
    "er",
    "je",
    "jes",
    "tje",
    "tjes",
}
_GLUED = re.compile(r"(\w{3,})['’‘\"“”„](\w+)")
_BEFORE_WORD = re.compile(r"(?:^|(?<=\s))’(?=\w)")


def quote_misread(ours: str, version: str) -> bool:
    """Whether `version` only adds a quote mark the print never sets so, where the layer has
    none: one gluing two words ("keeken" or "keek en" → "keek’en"), three letters or more
    before it and no contraction's end after (`_JOINED_ENDS`); or a closing ’ opening a word
    that elides nothing ("zet zijn" → "zet ’zijn", `quotes.ELISION`). In the trust data never
    the print (0 of 13, 0 of 7); a speck read as a mark."""
    for m in _GLUED.finditer(version):
        q = m.end(1)
        if m.group(2).lower() not in _JOINED_ENDS and ours in (
            version[:q] + version[q + 1 :],
            version[:q] + " " + version[q + 1 :],
        ):
            return True
    for m in _BEFORE_WORD.finditer(version):
        q = m.start()
        if not ELISION.match("'" + version[q + 1 :]) and ours == version[:q] + version[q + 1 :]:
            return True
    return False


def line_end_stop(
    ours: str,
    a0: int,
    a1: int,
    version: str,
    next_line: str,
    shortened: set[str],
    disputed: list[tuple[int, int]] | None = None,
) -> bool:
    """Whether `version` only ends a word on a full stop, for its comma or after it with no
    mark, where a lower-case word follows: at the line's end the next line's first, quote
    marks before it skipped; inside the line the very next letter, so an author's stop
    before a quotation opened in lower case ("stem. ‘dat") stays a question, and so does a
    next word a reading disputes (`disputed`, the line's other differences: the layer's
    "df" and "h" for an opening "'If" and "It"). No sentence ends there, so it is never
    the print, unless the word is one the book abbreviates (`abbreviations`)."""
    span = ours[a0:a1]
    if span.endswith(","):
        stopped = span[:-1] + "."
    elif span and (span[-1].isalnum() or span[-1] in "’'\"”"):
        stopped = span + "."
    else:
        return False
    if version != stopped:
        return False
    rest = ours[a1:]
    if rest.strip():
        if not rest[:1].isspace() or not rest.lstrip()[:1].islower():
            return False
        w0 = a1 + len(rest) - len(rest.lstrip())
        w1 = w0 + len(rest.split()[0])
        if any(d0 < w1 and w0 < d1 for d0, d1 in disputed or ()):
            return False
    else:
        first = _FIRST_LETTER.match(next_line.strip())
        if not first or not first.group(1).islower():
            return False
    word = re.findall(r"\w+", span)
    return not word or word[-1].lower() not in shortened


def known_versions(lexicon, read_as: list[str], continues: bool) -> tuple[bool | None, ...]:
    """Whether the word list knows each version, read as the word-list vote reads it:
    across a break hyphen with the next line's first word (`across`), so "dank-" is
    judged as "dankbaar", not left unjudged as a cut word."""
    return tuple(lexicon.verdict(v, continues) for v in read_as)


def across(version: str, joined: str) -> str:
    """A line's last word read with the next line's first: joined after a break hyphen
    ("dank-" + "baar" = "dankbaar"), else apart ("dank baar")."""
    if not joined:
        return version
    if version.endswith(HYPHENS):
        return version.rstrip("".join(HYPHENS)) + joined
    return f"{version} {joined}"


def hyphen_only(ours: str, a1: int, versions: list[str], next_line: str) -> str:
    """The next line's first word, where the versions end the line and differ only in a
    break hyphen; else ""."""
    words = next_line.split()
    if a1 != len(ours) or not words or not words[0][:1].isalpha():
        return ""
    stems = {v.rstrip("".join(HYPHENS)) for v in versions}
    hyphened = {v.endswith(HYPHENS) for v in versions}
    return words[0].rstrip(".,;:!?’”'\"") if len(stems) == 1 and len(hyphened) == 2 else ""


def supports(
    ours: str, reading: str, a0: int, a1: int, versions: list[str], curly: bool | None = None
) -> tuple[bool, ...]:
    """Whether a reading reads each version of the span `ours[a0:a1]`: its own differences
    there written into the whole span, which may be wider than they are, or, where it
    doesn't differ from `ours` there, ours (the first). `curly` is as `merged_differences`
    takes it."""
    if not reading:
        return tuple(False for _ in versions)
    mine = [d for d in differences(ours, reading) if d[0] < a1 and a0 < d[1]]
    piece = ours[a0:a1]
    for b0, b1, c0, c1 in sorted(mine, key=lambda d: -d[0]):
        piece = piece[: max(0, b0 - a0)] + reading[c0:c1] + piece[max(0, b1 - a0) :]
    if _curly(ours) or (curly and not _quoted(ours)):
        piece = _curled(piece, not ours[a1:].strip())
    return tuple(_alike(piece) == _alike(v) for v in versions)


def merged_differences(
    ours: str, others: list[str], curly: bool | None = None
) -> list[tuple[int, int, list[str]]]:
    """Spans of `ours` where any other reading differs, with each distinct other version.

    Overlapping differences from different readings become one span; a reading
    that agrees with `ours` there has no version of its own. A reading's straight quotes
    are curled where `ours` sets curly ones, or sets none in a book that does (`curly`).
    """
    found = [
        (a0, a1, b0, b1, r)
        for r, other in enumerate(others)
        for a0, a1, b0, b1 in differences(ours, other)
    ]
    groups: list[list] = []
    for d in sorted(found):
        if groups and d[0] <= max(g[1] for g in groups[-1]):
            groups[-1].append(d)
        else:
            groups.append([d])
    out = []
    for group in groups:
        g0, g1 = min(d[0] for d in group), max(d[1] for d in group)
        versions = []
        for r, other in enumerate(others):
            mine = sorted((d for d in group if d[4] == r), key=lambda d: -d[0])
            if not mine:
                continue
            piece = ours[g0:g1]
            for a0, a1, b0, b1, _ in mine:
                piece = piece[: a0 - g0] + other[b0:b1] + piece[a1 - g0 :]
            if _curly(ours) or (curly and not _quoted(ours)):
                piece = _curled(piece, not ours[g1:].strip())
            # Readings that differ only in quote, dash or ellipsis style are one version.
            folded = [_alike(v) for v in versions]
            if _alike(piece) != _alike(ours[g0:g1]) and _alike(piece) not in folded:
                versions.append(piece)
        if versions and (both := _combined(ours[g0:g1], versions)):
            versions.append(both)
        if versions and (capitals := _capitals(ours[g0:g1], versions)):
            versions.append(capitals)
        if versions:
            out.append((g0, g1, versions))
    return out


def _curly(text: str) -> bool:
    return any(c in text for c in "‘’“”") and not any(c in text for c in "'\"")


def _quoted(text: str) -> bool:
    return any(c in text for c in "‘’“”'\"")


def curly_book(pages: list[PageText]) -> bool:
    """Whether the layer sets more curly quote marks than straight ones."""
    text = "".join(ln.text for p in pages for ln in p.lines)
    return sum(text.count(c) for c in "‘’“”") > sum(text.count(c) for c in "'\"")


_WORDS = re.compile(r"[^\W_]+")


def _small_capitals(word: str) -> str | None:
    """The all-capitals form of a short word that small capitals could be read as
    ("vTM" → "VTM", "LC1" → "LCI": a 1 or 0 among more capitals is an I or O), else None.
    A word of more digits than letters is a number ("11", "10D") and stays one."""
    if not 2 <= len(word) <= 5:
        return None
    if word.isalpha():
        return word.upper() if word[1:] != word[1:].lower() else None
    letters = sum(c.isalpha() for c in word)
    if letters <= len(word) - letters:
        return None
    if word.isalnum() and set(word) & set("10") and word.translate(_LOOKALIKE).isupper():
        return word.translate(_LOOKALIKE)
    return None


_LOOKALIKE = str.maketrans("10", "IO")


def _capitals(ours: str, versions: list[str]) -> str | None:
    """One more version of a span: its first short word that mixes case inside, or a digit
    among capitals, in capitals, unless that form is already a version. The judges can only
    pick among the readings, and none has the capitals small capitals were set in."""
    for piece in (ours, *versions):
        form = _WORDS.sub(lambda m: _small_capitals(m[0]) or m[0], piece)
        if form != piece:
            folded = [_alike(v) for v in (ours, *versions)]
            return form if _alike(form) not in folded else None
    return None


_VOWELS = frozenset("aeiouyàáâäèéêëìíîïòóôöùúûü")
# A token: letters joined by hyphens, apostrophes or slashes ("ss-chef", "suv/mpv").
_TOKEN = re.compile(r"[^\W\d_]+(?:[-'’/][^\W\d_]+)*")
_LETTERS = re.compile(r"[^\W\d_]+")
_CONTRACTION = re.compile(r"[’'](?:t|re|ll|ve|d|m)\b")
# A word the book prints this often on its own, in lower case, is a word ("zo-", "foto-").
COMMON = 3


def book_words(pages: list[PageText]) -> Counter:
    """How often each word stands alone in the pages, as read."""
    return Counter(
        t
        for page in pages
        for line in page.lines
        for t in (w.strip(".,;:!?…“”‘’'\"()[]«»—–-") for w in line.text.split())
        if t.isalpha()
    )


def capital_pieces(token: str, words: Counter) -> list[tuple[int, int]]:
    """The pieces of a token small capitals may have been read as in lower case: a part of
    one to four letters joined to another ("ss-chef", "u-bocht", "usb-stick"), or a word of
    two to five letters with no vowel ("ss", "cv"). Not a contraction's part ("don't",
    "'s") nor a part with a vowel the book prints `COMMON` times on its own ("zo-")."""
    parts = list(_LETTERS.finditer(token))
    if len(parts) == 1:
        p = parts[0][0]
        return [(0, len(p))] if p.islower() and 2 <= len(p) <= 5 and not set(p) & _VOWELS else []
    out = []
    for m in parts:
        p, rest = m[0], token[m.end() :]
        if not p.islower() or len(p) > 4:
            continue
        if m.start() and token[m.start() - 1] in "’'":
            continue
        if _CONTRACTION.match(rest) or (p.endswith("n") and re.match(r"[’']t\b", rest)):
            continue
        if set(p) & _VOWELS and len(p) > 1 and words[p] >= COMMON:
            continue
        out.append((m.start(), m.end()))
    return out


def capitals_doubts(
    ours: str, taken: list[tuple[int, int]], words: Counter
) -> list[tuple[int, int, list[str]]]:
    """Spans of a line no reading disputes (outside `taken`) where small capitals may have
    been read in lower case, each with its capitals as the one other version. Every reader
    reads small capitals as lower case alike ("ss", "usb-stick"), so no difference raises
    them; the vision judges see which the scan prints. A token with two such pieces
    ("ss-chef") gets a version for each, as either may be the capitals."""
    out = []
    for m in _TOKEN.finditer(ours):
        pieces = capital_pieces(m[0], words)
        if not pieces:
            continue
        a0, a1 = _word_span(ours, m.start(), m.end())
        if any(t0 < a1 and a0 < t1 for t0, t1 in taken):
            continue
        span, at = ours[a0:a1], m.start() - a0
        out.append((a0, a1, [span[: at + p0] + span[at + p0 : at + p1].upper() + span[at + p1 :]
                             for p0, p1 in pieces]))  # fmt: skip
        taken = [*taken, (a0, a1)]
    return out


_TRAILING = re.compile(r"^(.*?)([.,;:!?…]*)([’”'\"]*)$", re.S)


def _combined(ours: str, versions: list[str]) -> str | None:
    """The word with every reading's trailing marks, where each reading lost a different one.

    Readings of the same word whose only differences are one punctuation mark
    and one closing quote, each missing from some ("zijn’", "zijn."), give the
    word with both ("zijn.’"), unless a reading already has it.
    """
    parts = [_TRAILING.match(v).groups() for v in (ours, *versions)]
    if len({core for core, _, _ in parts}) != 1:
        return None
    marks = {m for _, m, _ in parts if m}
    quotes = {q for _, _, q in parts if q}
    if len(marks) != 1 or len(quotes) != 1:
        return None
    both = parts[0][0] + marks.pop() + quotes.pop()
    return None if both == ours or both in versions else both


def _decide(
    pdf_page, number, k, ours, a0, a1, others, box, lang, vision, reader, cache, around=("", ""),
    vouched: int | None = None, joined: str = "", style: str = "", alarms=(),
    alarm_below: float = 1.0,
) -> tuple[tuple[str, str | None, dict[str, str]], dict[str, float]]:  # fmt: skip
    """\"ours\", \"other\" with the chosen version, or \"review\", with each model's pick;
    and each model's confidence in it.

    The text model also reads the lines `around` this one (before, after), where a
    quote opens or a sentence goes on. Where the versions differ only in a break
    hyphen, it reads the place across the break (`joined`): "dankbaar" or "dank baar".

    Where the word list knows the words of one version only (`vouched`, an index
    into the versions), that version is recorded as its vote. It decides nothing:
    acting on it saved questions on the tuning books and added unasked errors on
    held-out ones.

    A pick is applied when both models make it and the vision model is at least
    somewhat sure, or, where the versions differ only in punctuation, dashes or
    spacing (which a text model can't judge), when the vision model alone is sure.
    Anything else goes to a human.

    The vision judge sees the versions set off by ⟨ ⟩, which no version contains (“ ”
    looked like the marks they differ in), and is told the book's `style`. The text
    judge isn't: told the style, it picked right less often.
    """
    versions = [ours[a0:a1], *others]
    letters = "abcdefg"[: len(versions)]
    state = {"page": number, "line": k, "readings": versions, "box": [round(v, 1) for v in box]}
    question = {
        "reading": decide.choice(
            "The image is cut from a scanned printed book. Which text does it show, "
            "letter for letter, including quote marks, dashes and punctuation?"
            + (f" {style}" if style else ""),
            {**{c: f"exactly ⟨{v}⟩" for c, v in zip(letters, versions, strict=True)},
             "neither": "something else"},
        )
    }  # fmt: skip
    seen = _ask(vision, cache, state, question, image=lambda: _crop(pdf_page, box))
    language = LANGUAGE_NAMES.get(lang, "")
    lines = [ours[:a0] + across(v, joined) + ours[a1:] for v in versions]
    if joined:
        around = (around[0], around[1].split(maxsplit=1)[1] if " " in around[1].strip() else "")
    intro = "Two OCR readings" if len(lines) == 2 else "Several OCR readings"
    read = {"value": "", "confidence": 0.0}
    if reader is not None:
        read = _ask(
            reader,
            cache,
            {
                "line before": around[0],
                **dict(zip(letters, lines, strict=True)),
                "line after": around[1],
            },
            {
                "reading": decide.choice(
                    f"{intro} of the same line of a printed {language} book differ. "
                    "Which is the correct transcription, as printed, read between "
                    "the line before and the line after?",
                    {c: f"“{line}”" for c, line in zip(letters, lines, strict=True)},
                )
            },
        )
    pick = lambda value: versions[letters.index(value)] if value in letters else ""  # noqa: E731
    votes = {vision.model: pick(seen["value"])}
    confidence = {vision.model: seen["confidence"]}
    if reader is not None:
        votes[reader.model] = pick(read["value"])
        confidence[reader.model] = read["confidence"]
    for alarm in alarms if seen["confidence"] < alarm_below else ():
        wide = getattr(alarm, "wide", 0)
        asked = question
        if wide:
            asked = {
                n: {**q, "instructions": q["instructions"] + WIDE_NOTE} for n, q in question.items()
            }
        alarmed = _ask(alarm, cache, state, asked, image=lambda w=wide: _crop(pdf_page, box, w))
        votes[alarm.model] = pick(alarmed["value"])
        confidence[alarm.model] = alarmed["confidence"]
    if vouched is not None:
        votes["word list"] = versions[vouched]
    return _choose(versions, letters, seen, read, votes), confidence


def _choose(versions, letters, seen, read, votes) -> tuple[str, str | None, dict[str, str]]:
    """The fixed rule: both models agreeing, or the vision model alone on typography."""
    if _typographic(versions) and seen["value"] in letters and seen["confidence"] >= SURE_ALONE:
        if seen["value"] == "a":
            return "ours", None, votes
        return "other", versions[letters.index(seen["value"])], votes
    if seen["value"] == read["value"] and seen["confidence"] >= SURE:
        if seen["value"] == "a":
            return "ours", None, votes
        return "other", versions[letters.index(seen["value"])], votes
    return "review", None, votes


def _typographic(versions: list[str]) -> bool:
    """Whether the versions have the same words, differing only in what lies between them.

    Joining two words ("have never" → "havenever", "ik ’s" → "ik's") changes the words.
    """
    words = lambda v: tuple(re.findall(r"\w+(?:'\w+)*", v.translate(_FOLD)))  # noqa: E731
    return len({words(v) for v in versions}) == 1


def _ask(
    client: DecisionClient | decide.HostedClient,
    cache: DecisionCache,
    state: dict,
    questions: dict,
    image=None,
):
    key = DecisionCache.key(client.model, questions, state)
    if image is not None:
        crop = {"zoom": CROP_ZOOM, "pad": CROP_PAD}
        if wide := getattr(client, "wide", 0):
            crop["wide"] = wide
        readout = getattr(client, "fingerprint", "")
        keyed = {**state, "crop": crop, **({"readout": readout} if readout else {})}
        unkeyed = key if crop == UNKEYED_CROP and not readout else None
        key = DecisionCache.key(client.model, questions, keyed)
        answer = cache.get(key) or (cache.get(unkeyed) if unkeyed else None)
    else:
        answer = cache.get(key)
    if answer is None and isinstance(client, _Later):
        return {"value": "", "confidence": 0.0}
    if answer is None:
        a = client.decide(state, questions, image_png=image() if image else None)["reading"]
        answer = {"value": a.value, "confidence": a.confidence}
        if via := getattr(client, "via", ""):
            answer["via"] = via
        cache.put(key, answer)
    return answer


def _crop(pdf_page: pymupdf.Page, box, wide: float = 0) -> bytes:
    """The suspect's words, padded by `CROP_PAD`, or by `wide` points of its line either
    side (within the page), as judge set v2's wide crop."""
    side = wide or CROP_PAD
    clip = (pymupdf.Rect(box) + (-side, -CROP_PAD, side, CROP_PAD)) & pdf_page.rect
    return pdf_page.get_pixmap(matrix=pymupdf.Matrix(CROP_ZOOM, CROP_ZOOM), clip=clip).tobytes(
        "png"
    )


def apply(pages: list[PageText], suspects: list[Suspect]) -> list[PageText]:
    """Copies of the pages with the chosen fixes, on lines still reading as the text layer did."""
    fixes: dict[tuple[int, int], list[Suspect]] = {}
    for s in suspects:
        if s.choice == "other":
            fixes.setdefault((s.page, s.line), []).append(s)
    out = []
    for page in pages:
        lines = []
        for i, line in enumerate(page.lines):
            text = line.text
            here = [s for s in fixes.get((page.number, i), []) if s.original == text]
            lines.append(spliced(line, [(s.start, s.end, fixed_text(s, text)) for s in here]))
        out.append(replace(page, lines=lines))
    return out


def fixed_text(s: Suspect, text: str) -> str:
    """The text a fix puts in its span. A line's last word that loses only its hyphen keeps
    it where the word list knows the word the hyphen joins with the next line's ("Oran-" +
    "je"): the readers saw no hyphen, but the word goes on, and without one the joiner sets
    the next line after a space ("Oran je"). Where the joined form isn't a word ("is-" +
    "uitgesproken": a speck read as a hyphen) the fix stands. `text` is the line the fix is
    made in; every place that writes a fix into a line goes through this."""
    last = s.end == len(text) and text.endswith(HYPHENS) and len(text) > 1 and text[-2].isalpha()
    joins = bool(s.known) and s.known[0] is True and bool(s.joined)
    if last and joins and s.chosen == s.ours[:-1] and s.ours.endswith(text[-1]):
        return s.ours
    return _in_lines_quotes(s.chosen, text, s.end)


def _in_lines_quotes(chosen: str, text: str, end: int) -> str:
    """The chosen version with straight quote marks curled where its line sets more curly
    ones than straight: a reader writes straight marks, and Nervous System's "“T thought
    I'd" fixed to '"I' left an opening quote the quote check then asked about."""
    curly = sum(text.count(c) for c in "‘’“”")
    straight = sum(text.count(c) for c in "'\"")
    if not any(c in chosen for c in "'\"") or curly <= straight:
        return chosen
    return _curled(chosen, not text[end:].strip())


def save(suspects: list[Suspect], path: Path) -> None:
    write_atomic(path, json.dumps([asdict(s) for s in suspects], ensure_ascii=False, indent=1))
