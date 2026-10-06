"""Check a scan's OCR text layer against a second reading, line by line.

An OCR model (glm-ocr) reads the crop of each body line. Where its reading
differs from the text layer's (widened to whole words), the role model picks a
reading from the crop of the scan, and a text model picks the version of the
line that reads right. When both pick the same reading and the role model is at least somewhat
sure, it is applied; any other suspect is left to a human.

Fixes go into a copy of the pages, matched on the text layer's line text, so
the line texts the review keys its answers on stay as they are. Born-digital
PDFs, whose text is exact, aren't checked.
"""

import base64
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import httpx
import pymupdf
from rapidfuzz.distance import Levenshtein

from roboscriptorium.clients import ollaya
from roboscriptorium.clients.ollaya import OllayaClient
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import PageText
from roboscriptorium.roles import DecisionCache

DPI = 300
READING_VERSION = 1
READ_WORKERS = 4
LINE_PAD = 3  # points around a line's crop for the OCR model
MAX_LINE_TOKENS = 120
# Readings are written to the cache every so many lines, so a long run keeps its progress.
SAVE_EVERY = 200
# The role model must be at least this sure, and agree with the text model.
SURE = 0.3
CROP_ZOOM = 4
CROP_PAD = 4  # points around the suspect words
# Lines shorter than this are page numbers and scraps, not worth a second reading.
MIN_LINE_CHARS = 12
# Curly quotes as straight ones, one character for one, so offsets stay put.
_FOLD = str.maketrans("‘’“”", "''\"\"")
_OPENING_QUOTES = re.compile(r"(^|\s)[\"'‘’“”]+")
LANGUAGE_NAMES = {"nld": "Dutch", "eng": "English"}


@dataclass(frozen=True)
class Suspect:
    page: int
    line: int  # index into the text layer's lines
    original: str  # the line as the text layer reads it
    start: int  # the differing words, as a span of `original`
    end: int
    ours: str
    theirs: str
    box: tuple[float, float, float, float]
    choice: str  # "ours", "theirs", or "review"

    @property
    def alternative(self) -> str:
        return self.original[: self.start] + self.theirs + self.original[self.end :]


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
) -> dict[SourceRef, str]:
    """The OCR model's reading of each checked line's crop, cached on the line's text."""
    done: dict[str, str] = {}
    if cache.exists():
        raw = json.loads(cache.read_text())
        if raw.get("version") == READING_VERSION and raw.get("model") == model:
            done = raw["lines"]

    def key(page: PageText, k: int) -> str:
        text = page.lines[k].text
        return f"{page.number}:{k}:{hashlib.sha1(text.encode()).hexdigest()[:10]}"

    wanted = {
        SourceRef(p.number, k): (p, k)
        for p in pages
        for k, line in enumerate(p.lines)
        if SourceRef(p.number, k) in checked and len(line.text) >= MIN_LINE_CHARS
    }
    todo = [(p, k) for p, k in wanted.values() if key(p, k) not in done]

    def save() -> None:
        blob = {"version": READING_VERSION, "model": model, "lines": done}
        cache.write_text(json.dumps(blob, ensure_ascii=False))

    def read(item: tuple[PageText, int]) -> tuple[str, str]:
        page, k = item
        line = page.lines[k]
        clip = pymupdf.Rect(line.x0, line.y0, line.x1, line.y1) + (
            -LINE_PAD,
            -LINE_PAD,
            LINE_PAD,
            LINE_PAD,
        )
        with pymupdf.open(pdf) as doc:
            png = doc[page.number - 1].get_pixmap(dpi=DPI, clip=clip).tobytes("png")
        return key(page, k), read_line(png, model, ollama_url)

    with ThreadPoolExecutor(READ_WORKERS) as pool:
        for n, (k, text) in enumerate(pool.map(read, todo), 1):
            done[k] = text
            if n % SAVE_EVERY == 0:
                save()
    if todo:
        save()
    return {ref: done[key(p, k)] for ref, (p, k) in wanted.items()}


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
    tell them apart in a crop.
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
    ]


def _bare(text: str) -> str:
    return _OPENING_QUOTES.sub(r"\1", text.translate(_FOLD)).strip()


def _box(page_words: list, line, original: str, start: int, end: int):
    """The suspect words' box: the text layer's word boxes, or a share of the line's width."""
    words = sorted((w for w in page_words if _inside(w, line)), key=lambda w: w[0])
    tokens = original.split(" ")
    k0 = original[:start].count(" ")
    k1 = k0 + original[start:end].strip().count(" ") + 1
    if [w[4] for w in words] == tokens:
        picked = words[k0:k1]
        return (
            min(w[0] for w in picked),
            min(w[1] for w in picked),
            max(w[2] for w in picked),
            max(w[3] for w in picked),
        )
    width = line.x1 - line.x0
    return (
        line.x0 + width * start / len(original),
        line.y0,
        line.x0 + width * end / len(original),
        line.y1,
    )


def _inside(w, line) -> bool:
    cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
    return line.x0 - 3 <= cx <= line.x1 + 3 and line.y0 - 2 <= cy <= line.y1 + 2


def check(
    pdf: Path,
    pages: list[PageText],
    readings: dict[SourceRef, str],
    lang: str,
    vision: OllayaClient,
    reader: OllayaClient,
    cache: DecisionCache,
) -> list[Suspect]:
    """Suspects on the lines with a second reading, each with what to do about it."""
    suspects = []
    with pymupdf.open(pdf) as doc:
        for page in pages:
            pdf_page = doc[page.number - 1]
            page_words = pdf_page.get_text("words")
            for k, line in enumerate(page.lines):
                ours = line.text
                theirs = readings.get(SourceRef(page.number, k), "")
                if not theirs:
                    continue
                for a0, a1, b0, b1 in differences(ours, theirs):
                    box = _box(page_words, line, ours, a0, a1)
                    choice = _decide(
                        pdf_page,
                        page.number,
                        k,
                        ours,
                        a0,
                        a1,
                        theirs[b0:b1],
                        box,
                        lang,
                        vision,
                        reader,
                        cache,
                    )
                    suspects.append(
                        Suspect(
                            page.number, k, ours, a0, a1, ours[a0:a1], theirs[b0:b1], box, choice
                        )
                    )
    return suspects


def _decide(
    pdf_page, number, k, ours, a0, a1, theirs_part, box, lang, vision, reader, cache
) -> str:
    ours_part = ours[a0:a1]
    swapped = ours[:a0] + theirs_part + ours[a1:]
    seen = _ask(
        vision,
        cache,
        {
            "page": number,
            "line": k,
            "readings": [ours_part, theirs_part],
            "box": [round(v, 1) for v in box],
        },
        {
            "reading": ollaya.choice(
                "The image is cut from a scanned printed book. Which text does it show, "
                "letter for letter, including quote marks, dashes and punctuation?",
                {
                    "a": f"exactly “{ours_part}”",
                    "b": f"exactly “{theirs_part}”",
                    "neither": "something else",
                },
            )
        },
        image=lambda: _crop(pdf_page, box),
    )
    language = LANGUAGE_NAMES.get(lang, "")
    read = _ask(
        reader,
        cache,
        {"a": ours, "b": swapped},
        {
            "reading": ollaya.choice(
                f"Two OCR readings of the same line of a printed {language} book differ. "
                "Which is the correct transcription, as printed?",
                {"a": f"“{ours}”", "b": f"“{swapped}”"},
            )
        },
    )
    if seen["value"] == read["value"] and seen["confidence"] >= SURE:
        return {"a": "ours", "b": "theirs"}[seen["value"]]
    return "review"


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
    fixes: dict[tuple[int, str], list[Suspect]] = {}
    for s in suspects:
        if s.choice == "theirs":
            fixes.setdefault((s.page, s.original), []).append(s)
    out = []
    for page in pages:
        lines = []
        for line in page.lines:
            text = line.text
            # Right to left, so each fix leaves the spans before it in place.
            for s in sorted(fixes.get((page.number, text), []), key=lambda s: -s.start):
                text = text[: s.start] + s.theirs + text[s.end :]
            lines.append(replace(line, text=text) if text != line.text else line)
        out.append(replace(page, lines=lines))
    return out


def doubts(suspects: list[Suspect]) -> dict[tuple[int, str], list[str]]:
    """Per (page, line text), the other readings of a line a human should choose between."""
    out: dict[tuple[int, str], list[str]] = {}
    for s in suspects:
        if s.choice == "review":
            out.setdefault((s.page, s.original), []).append(s.alternative)
    return out


def save(suspects: list[Suspect], path: Path) -> None:
    path.write_text(json.dumps([asdict(s) for s in suspects], ensure_ascii=False, indent=1))
