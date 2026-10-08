"""Check a scan's OCR text layer against more readings, line by line.

More readings of each body line: glm-ocr on the line's crop (best on letters
and words), tesseract on the page (best on dashes) and, told the book's style,
qwen3.8 on the crop (best on quote marks). Where any differs from the text layer
(widened to whole words), the role model picks a version from the crop of the
scan, and a text model picks the version of the line that reads right. When both
pick the same reading and the role model is at least somewhat sure, it is
applied; any other suspect is left to a human.

Fixes go into a copy of the pages, matched on the text layer's line text, so
the line texts the review keys its answers on stay as they are. Born-digital
PDFs, whose text is exact, aren't checked.
"""

import base64
import csv
import hashlib
import io
import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

import httpx
import pymupdf
from rapidfuzz.distance import Levenshtein

from roboscriptorium import ocr
from roboscriptorium.clients import ollaya, openrouter
from roboscriptorium.clients.ollaya import OllayaClient
from roboscriptorium.files import write_atomic
from roboscriptorium.ir import SourceRef
from roboscriptorium.lexicon import Lexicon
from roboscriptorium.pdf import PageText, line_words, spells
from roboscriptorium.reflow import HYPHENS
from roboscriptorium.roles import DecisionCache

DPI = 300
READING_VERSION = 2
READ_WORKERS = 4
# A hosted model serves many requests at once.
HOSTED_WORKERS = 16
# Points above and below a line's crop for the OCR model. Crops also reach one em (the
# line's height) past each end, where a dash or quote the text layer missed is printed.
LINE_PAD = 3
# Points a neighbouring line's box may reach into that pad before the crop stops at it.
NEIGHBOUR_SLACK = 0.5
MAX_LINE_TOKENS = 120
# Readings are written to the cache every so many lines, so a long run keeps its progress.
SAVE_EVERY = 200
TESSERACT_VERSION = 1
TESSERACT_WORKERS = 6
# The role model must be at least this sure, and agree with the text model.
SURE = 0.3
# Where versions differ only in punctuation, dashes or spacing, the text model can't
# tell them apart; the vision model decides alone when at least this sure.
SURE_ALONE = 0.5
CROP_ZOOM = 4
CROP_PAD = 4  # points around the suspect words
# Curly quotes as straight ones, and a not sign (some OCR layers' line-end hyphen) as a
# hyphen, one character for one, so offsets stay put.
_FOLD = str.maketrans("‘’“”¬", "''\"\"-")
_OPENING_QUOTES = re.compile(r"(^|\s)[\"'‘’“”]+")
_ANY_DASH = re.compile(r"\s*[—–]\s*|\s+-\s+|\s+-(?=['\"]|$)")
_SPACE_BEFORE_APOSTROPHE = re.compile(r"(?<=\w) +'(?=\w)")
LANGUAGE_NAMES = {"nld": "Dutch", "eng": "English"}


@dataclass(frozen=True)
class Suspect:
    page: int
    line: int  # index into the text layer's lines
    original: str  # the line as the text layer reads it
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

    @property
    def across(self) -> list[str]:
        """The versions as read across the line break (`joined`), or as they are."""
        return [across(v, self.joined) for v in (self.ours, *self.others)]

    @property
    def alternatives(self) -> list[str]:
        """The line as each other reading has it."""
        return [self.original[: self.start] + o + self.original[self.end :] for o in self.others]


def scanned(pdf: Path, sample: int = 10) -> bool:
    """Whether the text layer is invisible OCR over page images (not born-digital text)."""
    invisible = visible = 0
    with pymupdf.open(pdf) as doc:
        step = max(1, doc.page_count // sample)
        for page in list(doc)[::step]:
            for span in page.get_texttrace():
                if span["type"] == 3:
                    invisible += len(span["chars"])
                else:
                    visible += len(span["chars"])
    return invisible > visible


def line_readings(
    pdf: Path,
    pages: list[PageText],
    checked: set[SourceRef],
    model: str,
    ollama_url: str,
    cache: Path,
    prompt: str = "",
    via: str = "",
) -> dict[SourceRef, str]:
    """The OCR model's reading of each checked line's crop, cached on the line's text.

    With a `prompt`, a generative vision model reads it (`transcribe`); without, glm-ocr
    (`read_line`). Short lines are read too: "keek.’" ends dialogue, and that is where a
    closing quote is lost. With `via`, another build of the same model reads the lines
    still to read; they are cached under `model` and listed under `via` in the cache."""
    done: dict[str, str] = {}
    read_by: dict[str, list[str]] = {}
    if cache.exists():
        raw = json.loads(cache.read_text())
        if (
            raw.get("version") == READING_VERSION
            and raw.get("model") == model
            and raw.get("prompt", "") == prompt
        ):
            done = raw["lines"]
            read_by = raw.get("via", {})

    with pymupdf.open(pdf) as doc:
        boxes = {p.number: line_boxes(doc[p.number - 1], p) for p in pages}

    def span(page: PageText, k: int) -> tuple[float, float]:
        return crop_span(boxes[page.number], k)

    def key(page: PageText, k: int) -> str:
        """The line's text and box, and the crop's span where a neighbour cuts it short:
        a crop that changes is read again."""
        box = boxes[page.number][k]
        text = hashlib.sha1(page.lines[k].text.encode()).hexdigest()[:10]
        out = f"{page.number}:{k}:{text}:" + ",".join(f"{v:.0f}" for v in box)
        top, bottom = span(page, k)
        if (top, bottom) != (box[1] - LINE_PAD, box[3] + LINE_PAD):
            out += f":{top:.1f}-{bottom:.1f}"
        return out

    wanted = {
        SourceRef(p.number, k): (p, k)
        for p in pages
        for k, line in enumerate(p.lines)
        if SourceRef(p.number, k) in checked and line.text.strip()
    }
    todo = [(p, k) for p, k in wanted.values() if key(p, k) not in done]

    def save() -> None:
        blob = {"version": READING_VERSION, "model": model, "prompt": prompt, "lines": done}
        if read_by:
            blob["via"] = read_by
        write_atomic(cache, json.dumps(blob, ensure_ascii=False))

    # PyMuPDF isn't thread-safe: crops are rendered here, a batch at a time, and
    # only the model calls run in the pool.
    reader = via or model
    workers = HOSTED_WORKERS if openrouter.hosted(reader) else READ_WORKERS
    with pymupdf.open(pdf) as doc, ThreadPoolExecutor(workers) as pool:
        for start in range(0, len(todo), SAVE_EVERY):
            batch = todo[start : start + SAVE_EVERY]
            crops = [
                _line_crop(doc, page.number, boxes[page.number][k], span(page, k))
                for page, k in batch
            ]
            if prompt:
                texts = pool.map(lambda png: transcribe(png, reader, ollama_url, prompt), crops)
            else:
                texts = pool.map(lambda png: read_line(png, reader, ollama_url), crops)
            for (page, k), text in zip(batch, texts, strict=True):
                done[key(page, k)] = text
                if via:
                    read_by.setdefault(via, []).append(key(page, k))
            save()
    return {ref: done[key(p, k)] for ref, (p, k) in wanted.items()}


def tesseract_readings(
    pdf: Path, pages: list[PageText], checked: set[SourceRef], lang: str, cache: Path
) -> dict[SourceRef, str]:
    """Tesseract's reading of each checked line: its words whose centres fall in the line."""
    words = tesseract_words(pdf, [p.number for p in pages], lang, cache)
    with pymupdf.open(pdf) as doc:
        boxes = {p.number: line_boxes(doc[p.number - 1], p) for p in pages}
    out = {}
    for page in pages:
        for k, found in enumerate(_by_line(boxes[page.number], words[page.number])):
            ref = SourceRef(page.number, k)
            if ref in checked and page.lines[k].text.strip():
                out[ref] = " ".join(w[0] for w in found)
    return out


def tesseract_words(
    pdf: Path, numbers: list[int], lang: str, cache: Path
) -> dict[int, list[tuple[str, float, float, float, float]]]:
    """Tesseract's words with their boxes in points, per page, cached."""
    done: dict[int, list] = {}
    if cache.exists():
        raw = json.loads(cache.read_text())
        if raw.get("version") == TESSERACT_VERSION and raw.get("lang") == lang:
            done = {int(n): [tuple(w) for w in ws] for n, ws in raw["pages"].items()}
    todo = [n for n in numbers if n not in done]
    if todo:
        # Pages are rendered on this thread (PyMuPDF isn't thread-safe); tesseract runs pooled.
        with pymupdf.open(pdf) as doc, ThreadPoolExecutor(TESSERACT_WORKERS) as pool:
            for start in range(0, len(todo), TESSERACT_WORKERS):
                batch = todo[start : start + TESSERACT_WORKERS]
                images = [doc[n - 1].get_pixmap(dpi=DPI).tobytes("png") for n in batch]
                read = pool.map(lambda png: _tesseract_page(png, lang), images)
                for n, page_words in zip(batch, read, strict=True):
                    done[n] = page_words
        blob = {"version": TESSERACT_VERSION, "lang": lang, "pages": done}
        write_atomic(cache, json.dumps(blob, ensure_ascii=False))
    return {n: done[n] for n in numbers}


def _tesseract_page(png: bytes, lang: str) -> list[tuple[str, float, float, float, float]]:
    out = ocr.tesseract(png, lang, tsv=True)
    rows = csv.DictReader(io.StringIO(out), delimiter="\t", quoting=csv.QUOTE_NONE)
    if out and "level" not in (rows.fieldnames or []):
        raise ValueError(f"tesseract gave no word table: {out[:200]!r}")
    scale = 72 / DPI
    words = []
    for row in rows:
        text = (row.get("text") or "").strip()
        if row["level"] == "5" and text:
            x, y, w, h = (int(row[k]) * scale for k in ("left", "top", "width", "height"))
            words.append((text, x, y, x + w, y + h))
    return words


def _by_line(boxes: list, words) -> list[list[tuple[str, float, float, float, float]]]:
    """Tesseract's words per line: the nearest line box (widened a little) holding the centre."""
    out = [[] for _ in boxes]
    for w in words:
        cx, cy = (w[1] + w[3]) / 2, (w[2] + w[4]) / 2
        holding = [
            k
            for k, b in enumerate(boxes)
            if b[0] - 3 <= cx <= b[2] + 3 and b[1] - 2 <= cy <= b[3] + 2
        ]
        if holding:
            out[min(holding, key=lambda k: abs((boxes[k][1] + boxes[k][3]) / 2 - cy))].append(w)
    return [sorted(ws, key=lambda w: w[1]) for ws in out]


def crop_span(boxes: list, k: int) -> tuple[float, float]:
    """The top and bottom of line k's crop: LINE_PAD beyond its box, but not into the box
    of a line above or below it in the same column, where a reader would read that line
    too. A neighbour reaching less than NEIGHBOUR_SLACK into the pad leaves it whole."""
    x0, y0, x1, y1 = boxes[k]
    top, bottom = y0 - LINE_PAD, y1 + LINE_PAD
    for j, (a0, b0, a1, b1) in enumerate(boxes):
        if j == k or a1 <= x0 or x1 <= a0:
            continue
        if b0 + b1 < y0 + y1:
            if b1 - top > NEIGHBOUR_SLACK:
                top = max(top, min(b1, y0))
        elif bottom - b0 > NEIGHBOUR_SLACK:
            bottom = min(bottom, max(b0, y1))
    return top, bottom


def _line_crop(
    doc: pymupdf.Document, number: int, box, span: tuple[float, float] | None = None
) -> bytes:
    """A line's crop: one em past either end, and `span` (`crop_span`) or LINE_PAD above
    and below."""
    em = box[3] - box[1]
    top, bottom = span or (box[1] - LINE_PAD, box[3] + LINE_PAD)
    clip = pymupdf.Rect(box[0] - em, top, box[2] + em, bottom)
    return doc[number - 1].get_pixmap(dpi=DPI, clip=clip).tobytes("png")


def line_boxes(pdf_page: pymupdf.Page, page: PageText) -> list[tuple[float, float, float, float]]:
    """Each line's box as printed: its words' boxes together where they spell the line.

    Some OCR layers give lines boxes far taller than the print.
    """
    out = []
    for line, words in zip(page.lines, line_words(pdf_page.get_text("words"), page), strict=True):
        if words and spells(words, line.text):
            out.append(_union(words))
        else:
            out.append((line.x0, line.y0, line.x1, line.y1))
    return out


def _union(words) -> tuple[float, float, float, float]:
    return (
        min(w[0] for w in words),
        min(w[1] for w in words),
        max(w[2] for w in words),
        max(w[3] for w in words),
    )


def read_line(png: bytes, model: str, ollama_url: str) -> str:
    """The OCR model's reading of one printed line.

    glm-ocr's Ollama template has no stop token, so after the line it starts over;
    the reading ends at its first line break. It sometimes writes a printed em
    dash as the CJK character 一, which looks the same.
    """
    payload = {
        "model": model,
        "prompt": "Text Recognition:",
        "images": [base64.b64encode(png).decode()],
        "options": {"num_predict": MAX_LINE_TOKENS},
    }
    out = ""
    with httpx.stream("POST", f"{ollama_url}/api/generate", json=payload, timeout=300) as resp:
        resp.raise_for_status()
        for chunk in resp.iter_lines():
            if chunk:
                out += json.loads(chunk).get("response", "")
            if "\n" in out.strip():
                break
    return out.strip().split("\n")[0].strip().replace("一", "—")


def transcribe(png: bytes, model: str, ollama_url: str, prompt: str) -> str:
    """A generative vision model's transcription of one printed line, thinking off: on
    Ollama, or hosted when the model is named `openrouter:…`."""
    if openrouter.hosted(model):
        text = openrouter.transcribe(png, model, prompt, MAX_LINE_TOKENS)
        return text.strip().split("\n")[0].strip()
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [base64.b64encode(png).decode()],
        "stream": False,
        "think": False,
        "options": {"num_predict": MAX_LINE_TOKENS, "temperature": 0},
    }
    resp = httpx.post(f"{ollama_url}/api/generate", json=payload, timeout=600)
    resp.raise_for_status()
    return resp.json()["response"].strip().split("\n")[0].strip()


def _word_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start > 0 and text[start - 1] != " ":
        start -= 1
    while end < len(text) and text[end] != " ":
        end += 1
    return start, end


def differences(ours: str, theirs: str) -> list[tuple[int, int, int, int]]:
    """Where two readings of a line differ, widened to whole words, as spans of each.

    Curly and straight quotes count as the same. A difference only in opening
    quote marks isn't one: OCR models read a printed “ as ‘, and no model can
    tell them apart in a crop. Nor is a reading without the space before an
    apostrophe ("uur’s" for "uur ’s"): OCR models miss the narrow space Dutch
    print sets before the article ’s, and no judge sees it in a crop. Nor are
    differences in a dash's kind or the space around it: a book sets all its dashes
    one way (`typography.py`).
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
        and _dashes(ours[s[0] : s[1]]) != _dashes(theirs[s[2] : s[3]])
    ]


def _dashes(text: str) -> str:
    """Text with every dash between words alike: the book's dash style is set book-wide."""
    return _ANY_DASH.sub("—", text.translate(_FOLD)).strip()


def _bare(text: str) -> str:
    return _OPENING_QUOTES.sub(r"\1", text.translate(_FOLD)).strip()


def _box(words: list, box, original: str, start: int, end: int):
    """The suspect words' box: the text layer's word boxes, or a share of the line's box.

    At the line's start or end it reaches one em further, where a mark the text
    layer missed is printed.
    """
    k0 = original[:start].count(" ")
    k1 = k0 + original[start:end].strip().count(" ") + 1
    x0, y0, x1, y1 = box
    if spells(words, original):
        out = list(_union(words[k0:k1]))
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
    vision: OllayaClient,
    reader: OllayaClient,
    cache: DecisionCache,
    lexicon: Lexicon | None = None,
    style: str = "",
) -> list[Suspect]:
    """Suspects where any other reading (by name) differs from the text layer, each with a
    decision. `style` tells the vision judge how the book is set (`quotes.style_note`)."""
    suspects = []
    with pymupdf.open(pdf) as doc:
        for page in pages:
            pdf_page = doc[page.number - 1]
            words = line_words(pdf_page.get_text("words"), page)
            boxes = line_boxes(pdf_page, page)
            for k, line in enumerate(page.lines):
                ours = line.text
                others = {n: r.get(SourceRef(page.number, k), "") for n, r in readings.items()}
                read = [o for o in others.values() if o]
                for a0, a1, alternatives in merged_differences(ours, read):
                    versions = [ours[a0:a1], *alternatives]
                    box = _box(words[k], boxes[k], ours, a0, a1)
                    around = (
                        page.lines[k - 1].text if k > 0 else "",
                        page.lines[k + 1].text if k + 1 < len(page.lines) else "",
                    )
                    continues = a0 == 0 and k > 0 and page.lines[k - 1].text.endswith(HYPHENS)
                    joined = hyphen_only(ours, a1, versions, around[1])
                    read_as = [across(v, joined) for v in versions]
                    (choice, chosen, votes), confidence = _decide(
                        pdf_page, page.number, k, ours, a0, a1, alternatives, box, lang,
                        vision, reader, cache, around,
                        lexicon.vouches(read_as, continues) if lexicon else None,
                        joined, style,
                    )  # fmt: skip
                    support = {
                        n: supports(ours, other, a0, a1, versions) for n, other in others.items()
                    }
                    known = (
                        tuple(lexicon.verdict(v, continues) for v in versions) if lexicon else ()
                    )
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
                        )  # fmt: skip
                    )
    return suspects


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


def supports(ours: str, reading: str, a0: int, a1: int, versions: list[str]) -> tuple[bool, ...]:
    """Whether a reading reads each version of the span `ours[a0:a1]`: one of its own
    versions there, or, where it doesn't differ from `ours` there, ours (the first)."""
    if not reading:
        return tuple(False for _ in versions)
    mine = [
        v for b0, b1, vs in merged_differences(ours, [reading]) if b0 < a1 and a0 < b1 for v in vs
    ]
    return tuple(v in mine or (k == 0 and not mine) for k, v in enumerate(versions))


def merged_differences(ours: str, others: list[str]) -> list[tuple[int, int, list[str]]]:
    """Spans of `ours` where any other reading differs, with each distinct other version.

    Overlapping differences from different readings become one span; a reading
    that agrees with `ours` there has no version of its own.
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
            if _curly(ours):
                piece = _curled(piece)
            # Readings that differ only in quote style are one version.
            folded = [v.translate(_FOLD) for v in versions]
            if piece.translate(_FOLD) != ours[g0:g1].translate(_FOLD) and (
                piece.translate(_FOLD) not in folded
            ):
                versions.append(piece)
        if versions and (both := _combined(ours[g0:g1], versions)):
            versions.append(both)
        if versions:
            out.append((g0, g1, versions))
    return out


def _curly(text: str) -> bool:
    return any(c in text for c in "‘’“”") and not any(c in text for c in "'\"")


def _curled(text: str) -> str:
    """Straight quotes as curly ones: opening at a word's start, closing elsewhere."""
    text = re.sub(r"(^|\s)'", r"\1‘", text)
    text = re.sub(r"(^|\s)\"", r"\1“", text)
    return text.replace("'", "’").replace('"', "”")


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
    vouched: int | None = None, joined: str = "", style: str = "",
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
    seen = _ask(
        vision,
        cache,
        {
            "page": number,
            "line": k,
            "readings": versions,
            "box": [round(v, 1) for v in box],
        },
        {
            "reading": ollaya.choice(
                "The image is cut from a scanned printed book. Which text does it show, "
                "letter for letter, including quote marks, dashes and punctuation?"
                + (f" {style}" if style else ""),
                {**{c: f"exactly ⟨{v}⟩" for c, v in zip(letters, versions, strict=True)},
                 "neither": "something else"},
            )
        },
        image=lambda: _crop(pdf_page, box),
    )  # fmt: skip
    language = LANGUAGE_NAMES.get(lang, "")
    lines = [ours[:a0] + across(v, joined) + ours[a1:] for v in versions]
    if joined:
        around = (around[0], around[1].split(maxsplit=1)[1] if " " in around[1].strip() else "")
    intro = "Two OCR readings" if len(lines) == 2 else "Several OCR readings"
    read = _ask(
        reader,
        cache,
        {
            "line before": around[0],
            **dict(zip(letters, lines, strict=True)),
            "line after": around[1],
        },
        {
            "reading": ollaya.choice(
                f"{intro} of the same line of a printed {language} book differ. "
                "Which is the correct transcription, as printed, read between "
                "the line before and the line after?",
                {c: f"“{line}”" for c, line in zip(letters, lines, strict=True)},
            )
        },
    )
    pick = lambda value: versions[letters.index(value)] if value in letters else ""  # noqa: E731
    votes = {vision.model: pick(seen["value"]), reader.model: pick(read["value"])}
    confidence = {vision.model: seen["confidence"], reader.model: read["confidence"]}
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


def _ask(client: OllayaClient, cache: DecisionCache, state: dict, questions: dict, image=None):
    key = DecisionCache.key(client.model, questions, state)
    answer = cache.get(key)
    if answer is None:
        a = client.decide(state, questions, image_png=image() if image else None)["reading"]
        answer = {"value": a.value, "confidence": a.confidence}
        cache.put(key, answer)
    return answer


def _crop(pdf_page: pymupdf.Page, box) -> bytes:
    clip = pymupdf.Rect(box) + (-CROP_PAD, -CROP_PAD, CROP_PAD, CROP_PAD)
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
            # Right to left, so each fix leaves the spans before it in place.
            for s in sorted(here, key=lambda s: -s.start):
                text = text[: s.start] + s.chosen + text[s.end :]
            lines.append(replace(line, text=text) if text != line.text else line)
        out.append(replace(page, lines=lines))
    return out


@dataclass(frozen=True)
class Doubt:
    """One place in a line where the readings differ and no model settled it: one question."""

    page: int
    line: int  # index into the text layer's lines
    original: str  # the line as the text layer reads it
    start: int  # the place, as a span of `original`
    end: int
    box: tuple[float, float, float, float]
    # The whole line as each reading has it here (the text layer's first), with the
    # models that picked it; the rest of the line as the text layer reads it.
    readings: list[tuple[str, list[str]]]
    # For a break hyphen: the next line's first word, which the readings end with.
    joined: str = ""


def doubts(suspects: list[Suspect]) -> list[Doubt]:
    """A question per place a human should settle."""
    out = []
    for s in suspects:
        if s.choice != "review":
            continue
        readings: list[tuple[str, list[str]]] = []
        for version in (s.ours, *s.others):
            line = s.original[: s.start] + across(version, s.joined) + s.original[s.end :]
            voters = [model for model, picked in s.votes.items() if picked == version]
            known = next((r for r in readings if r[0] == line), None)
            if known is None:
                readings.append((line, voters))
            else:
                known[1].extend(v for v in voters if v not in known[1])
        out.append(Doubt(s.page, s.line, s.original, s.start, s.end, s.box, readings, s.joined))
    return out


def save(suspects: list[Suspect], path: Path) -> None:
    write_atomic(path, json.dumps([asdict(s) for s in suspects], ensure_ascii=False, indent=1))
