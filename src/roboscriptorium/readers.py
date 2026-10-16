"""Readings of a page's lines besides the text layer: crops of each line, read by
glm-ocr (`read_line`), a generative vision model told the book's style (`transcribe`) and
tesseract (`tesseract_readings`), each cached per book (keyed on a line's page, text and
box, never its position). The OCR check (`ocrcheck.py`) compares them."""

import base64
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pymupdf

from roboscriptorium import ocr
from roboscriptorium.clients import openrouter
from roboscriptorium.clients.retry import patiently
from roboscriptorium.files import read_cache, write_atomic, write_cache
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import PageText, line_words, page_words, spells

DPI = 300


# Readings are keyed on a line's page, text and box (`line_key`); version 2 keys also held
# its position on the page, and are converted on load (`_current`).
READING_VERSION = 3


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


def _shelf(cache: Path, model: str, prompt: str) -> Path:
    """Where readings by another model or prompt than the cache's are kept aside."""
    tag = hashlib.sha1(f"{model}\n{prompt}".encode()).hexdigest()[:10]
    return cache.with_name(f"{cache.stem}.{tag}{cache.suffix}")


def _readings(cache: Path, model: str, prompt: str) -> dict | None:
    """The cached readings by `model` with `prompt`, or None. The cache holds one model
    and prompt; readings by another are moved to their shelf rather than lost, and come
    back from it when asked for again (a slice and its whole book may differ)."""
    if not cache.exists():
        return None
    raw = _current(json.loads(cache.read_text()))
    if raw is None:
        return None
    if raw.get("model") == model and raw.get("prompt", "") == prompt:
        return raw
    shelved = _shelf(cache, raw.get("model", ""), raw.get("prompt", ""))
    write_atomic(shelved, json.dumps(raw, ensure_ascii=False))
    shelf = _shelf(cache, model, prompt)
    if shelf.exists():
        return _current(json.loads(shelf.read_text()))
    return None


def _current(raw: dict) -> dict | None:
    """A readings cache in the current format: a version 2 one with its keys' line
    positions taken out, anything older None."""
    if raw.get("version") == READING_VERSION:
        return raw
    if raw.get("version") != 2:
        return None

    def key(old: str) -> str:
        page, _, rest = old.split(":", 2)
        return f"{page}:{rest}"

    out = {**raw, "version": READING_VERSION, "lines": {key(k): v for k, v in raw["lines"].items()}}
    if "via" in raw:
        out["via"] = {m: [key(k) for k in keys] for m, keys in raw["via"].items()}
    return out


def line_key(page: PageText, boxes: list, k: int) -> str:
    """The key a line's reading is cached under: its page, text and box, and the crop's
    span where a neighbour cuts it short, so a crop that changes is read again. Not its
    position: a line inserted above it leaves its reading in place."""
    box = boxes[k]
    text = hashlib.sha1(page.lines[k].text.encode()).hexdigest()[:10]
    out = f"{page.number}:{text}:" + ",".join(f"{v:.0f}" for v in box)
    top, bottom = crop_span(boxes, k)
    if (top, bottom) != (box[1] - LINE_PAD, box[3] + LINE_PAD):
        out += f":{top:.1f}-{bottom:.1f}"
    return out


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
    (`read_line`); either reading is given in Latin letters (`ocr.latin`). Short lines are
    read too: "keek.’" ends dialogue, and that is where a closing quote is lost. With
    `via`, another build of the same model reads the lines still to read; they are cached
    under `model` and listed under `via` in the cache."""
    done: dict[str, str] = {}
    read_by: dict[str, list[str]] = {}
    raw = _readings(cache, model, prompt)
    if raw is not None:
        done = raw["lines"]
        read_by = raw.get("via", {})

    with pymupdf.open(pdf) as doc:
        boxes = {p.number: line_boxes(doc[p.number - 1], p) for p in pages}

    def span(page: PageText, k: int) -> tuple[float, float]:
        return crop_span(boxes[page.number], k)

    def key(page: PageText, k: int) -> str:
        return line_key(page, boxes[page.number], k)

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
            try:
                for (page, k), text in zip(batch, texts, strict=True):
                    done[key(page, k)] = text
                    if via:
                        read_by.setdefault(via, []).append(key(page, k))
            finally:
                save()  # a reading that fails loses itself, not the batch before it
    return {ref: ocr.latin(done[key(p, k)]) for ref, (p, k) in wanted.items()}


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
    if raw := read_cache(cache, TESSERACT_VERSION, lang=lang):
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
                write_cache(cache, TESSERACT_VERSION, {"pages": done}, lang=lang)
    return {n: done[n] for n in numbers}


def _tesseract_page(png: bytes, lang: str) -> list[tuple[str, float, float, float, float]]:
    return ocr.tesseract_words(png, lang, DPI)


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
    for line, words in zip(page.lines, line_words(page_words(pdf_page), page), strict=True):
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

    def read() -> str:
        out = ""
        with httpx.stream("POST", f"{ollama_url}/api/generate", json=payload, timeout=300) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_lines():
                if chunk:
                    out += json.loads(chunk).get("response", "")
                if "\n" in out.strip():
                    break
        return out

    return patiently(read).strip().split("\n")[0].strip().replace("一", "—")


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
    resp = patiently(lambda: httpx.post(f"{ollama_url}/api/generate", json=payload, timeout=600))
    resp.raise_for_status()
    return resp.json()["response"].strip().split("\n")[0].strip()
