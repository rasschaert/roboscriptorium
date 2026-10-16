"""Whole-page readings, split back into the text layer's lines: two more readers for the
OCR check.

glm-ocr and Qwen each read a body page whole, cached per page. A reading is aligned to
the layer's words page-wide, and each line gets the words that align to it, so the OCR
check sees a page reading as it sees a line reader's (docs/design.md, "Page readers").
A word the layer breaks over a line end is split where the layer breaks it.
"""

import base64
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pymupdf
from rapidfuzz.distance import Levenshtein

from roboscriptorium import ocr
from roboscriptorium.clients.retry import patiently
from roboscriptorium.files import write_atomic
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import PDF_LOCK, PageText
from roboscriptorium.reflow import HYPHENS

VERSION = 1
# A page rendered at this many pixels: glm-ocr reads it near-exactly, and it fits
# Ollama's 32k context shared by four slots.
PIXELS = 1_600_000
MAX_TOKENS = 1500
# glm-ocr serves four requests at once on llama.cpp; Qwen's MLX runner one.
GLM_WORKERS = 4
# A reading that matches fewer of the layer's words than this is of another page or
# invented (glm-ocr on a near-empty page): it reads no line.
MIN_MATCHED = 0.5
# Words a reading has between two of the layer's: a few go to the line before (a word
# the layer lost); more are a running head, a caption or invented text, and are dropped.
MAX_INSERTED = 2
_AFTER_DASH = re.compile(r"(?<=[—–])(?=\w)")
GLM_PROMPT = "Text Recognition:"
PROMPT = (
    "Transcribe this printed book page exactly as printed: the same words, spelling, "
    "accents and punctuation, including the print's own quote marks and dashes. Leave out "
    "page numbers, running heads and any text inside pictures. Write a picture's caption "
    "as its own paragraph. Join a word the print breaks over a line end with a hyphen "
    "into one word; keep a hyphen that belongs to the word. Separate paragraphs with one "
    "blank line; within a paragraph write the text as one line. Mark a chapter heading "
    "with '# '. Output only the transcription."
)


def _glm(model: str) -> bool:
    return model.startswith("glm-ocr")


def read_page(png: bytes, model: str, ollama_url: str) -> str:
    """The model's reading of a whole page, thinking off.

    glm-ocr has no stop token: it reads the page again until Ollama aborts on the
    repeats ("token repeat limit reached"), so it is streamed and cut where it starts
    over (`once`)."""
    payload = {
        "model": model,
        "prompt": GLM_PROMPT if _glm(model) else PROMPT,
        "images": [base64.b64encode(png).decode()],
        "options": {"temperature": 0, "num_predict": MAX_TOKENS},
    }
    if not _glm(model):

        def generate() -> str:
            body = {**payload, "stream": False, "think": False}
            resp = httpx.post(f"{ollama_url}/api/generate", json=body, timeout=900)
            resp.raise_for_status()
            return resp.json()["response"]

        return patiently(generate)

    def stream() -> str:
        out = ""
        with httpx.stream("POST", f"{ollama_url}/api/generate", json=payload, timeout=900) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_lines():
                if chunk:
                    part = json.loads(chunk)
                    out += part.get("response", "")
                    if part.get("error"):
                        break
        return once(out)

    return patiently(stream)


def once(text: str) -> str:
    """The text up to where it starts over."""
    head = text.strip()[:60]
    again = text.find(head, len(head)) if len(head) >= 20 else -1
    return text[:again] if again > 0 else text


def page_readings(
    pdf: Path, numbers: list[int], model: str, ollama_url: str, cache: Path
) -> dict[int, str]:
    """Each page's reading by `model`, cached per page under the model, prompt and size."""
    prompt = GLM_PROMPT if _glm(model) else PROMPT
    done: dict[str, str] = {}
    if cache.exists():
        kept = json.loads(cache.read_text())
        if (kept.get("version"), kept.get("model"), kept.get("prompt"), kept.get("pixels")) == (
            VERSION,
            model,
            prompt,
            PIXELS,
        ):
            done = kept["pages"]
    todo = [n for n in numbers if str(n) not in done]

    def save() -> None:
        blob = {"version": VERSION, "model": model, "prompt": prompt, "pixels": PIXELS}
        write_atomic(cache, json.dumps({**blob, "pages": done}, ensure_ascii=False))

    workers = GLM_WORKERS if _glm(model) else 1
    with pymupdf.open(pdf) as doc, ThreadPoolExecutor(workers) as pool:
        for start in range(0, len(todo), workers):
            batch = todo[start : start + workers]
            with PDF_LOCK:
                pngs = [_render(doc[n - 1]) for n in batch]
            texts = pool.map(lambda png: read_page(png, model, ollama_url), pngs)
            try:
                for n, text in zip(batch, texts, strict=True):
                    done[str(n)] = text
            finally:
                save()
    return {n: done[str(n)] for n in numbers}


def _render(page: pymupdf.Page) -> bytes:
    zoom = (PIXELS / (page.rect.width * page.rect.height)) ** 0.5
    return page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png")


def _key(word: str) -> str:
    """What two readings of a word are compared on: its letters and digits, lower case."""
    letters = "".join(c for c in word.lower() if c.isalnum())
    return letters or word


def _pieces(word: str) -> list[str]:
    """A word cut after each dash that runs into the next word ("fast—and"): a dash one
    reading sees and another misses then costs one word, not two."""
    return _AFTER_DASH.split(word)


def reading_words(text: str) -> list[tuple[str, bool]]:
    """A page reading's words without Markdown, each with whether the next word follows
    it without a space (`_pieces`); a word broken over a line end with a hyphen joined
    into one, hyphen kept ("onge-opend")."""
    out: list[tuple[str, bool]] = []
    broken = False
    for line in text.splitlines():
        line = re.sub(r"^\s*#+\s*", "", line)
        line = re.sub(r"[*_]{1,2}(\S[^*_]*?)[*_]{1,2}", r"\1", line)
        words = line.split()
        if broken and words and words[0][:1].islower():
            last = out.pop()[0]
            words[0] = last + words[0]
        for w in words:
            parts = _pieces(w)
            out += [(part, i + 1 < len(parts)) for i, part in enumerate(parts)]
        broken = bool(words) and len(words[-1]) > 1 and words[-1][-1] in "-¬"
    return out


def _layer_words(page: PageText) -> list[list[tuple[int, str]]]:
    """The layer's words in reading order, each as its pieces (line, text): a word
    broken over a line end with a hyphen is one word of two pieces."""
    out: list[list[tuple[int, str]]] = []
    carry = False
    for k, line in enumerate(page.lines):
        words = [p for w in line.text.split() for p in _pieces(w)]
        for i, w in enumerate(words):
            if carry and i == 0:
                out[-1].append((k, w))
            else:
                out.append([(k, w)])
        carry = bool(words) and words[-1][-1] in HYPHENS and len(words[-1]) > 1
    return out


def _split(word: str, pieces: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """A reading's word for a layer word of two pieces: cut after as many letters as the
    first piece has, the layer's line-end hyphen kept on the first part."""
    first, rest = pieces[0][1], pieces[1:]
    want = len(_key(first[:-1]))
    seen = cut = 0
    while cut < len(word) and seen < want:
        seen += word[cut].isalnum()
        cut += 1
    tail = word[cut:].lstrip("-¬")
    if not tail:
        return [(pieces[0][0], word)]
    return [(pieces[0][0], word[:cut] + first[-1]), (rest[0][0], tail)]


def split_lines(page: PageText, reading: str) -> dict[int, str]:
    """The page reading split into the layer's lines: each line index with the words
    that align to it. Empty when the reading matches too few of the layer's words."""
    layer = _layer_words(page)
    words = reading_words(reading)
    if not layer or not words:
        return {}
    ops = Levenshtein.opcodes(
        ["".join(_key(t) for _, t in pieces) for pieces in layer], [_key(w) for w, _ in words]
    )
    matched = sum(op.src_end - op.src_start for op in ops if op.tag == "equal")
    if matched < MIN_MATCHED * len(layer):
        return {}
    got: dict[int, str] = {}
    glued: dict[int, bool] = {}

    def give(pieces: list[tuple[int, str]], word: tuple[str, bool], whole: bool) -> None:
        text, glue = word
        parts = _split(text, pieces) if whole and len(pieces) > 1 else [(pieces[0][0], text)]
        for k, part in parts:
            gap = "" if glued.get(k, True) else " "
            got[k] = got.get(k, "") + gap + part
            glued[k] = glue

    for op in ops:
        n, m = op.src_end - op.src_start, op.dest_end - op.dest_start
        if op.tag == "delete":
            continue
        if op.tag == "insert":
            if m > MAX_INSERTED:
                continue
            at = layer[op.src_start - 1][-1:] if op.src_start else layer[0][:1]
            for j in range(op.dest_start, op.dest_end):
                give(at, words[j], False)
            continue
        # equal or replace: each reading word to the layer word at its share of the run
        for j in range(m):
            i = op.src_start + (j if n == m else j * n // m)
            give(layer[i], words[op.dest_start + j], n == m)
    return got


def line_readings(
    pdf: Path,
    pages: list[PageText],
    checked: set[SourceRef],
    model: str,
    ollama_url: str,
    cache: Path,
) -> dict[SourceRef, str]:
    """Each checked line as `model`'s page reading reads it; a line the reading has no
    words for is left out, as is every line of a page whose reading doesn't match. Any
    Cyrillic letter in it is transliterated (`ocr.latin`)."""
    wanted = [
        p for p in pages if any(SourceRef(p.number, k) in checked for k in range(len(p.lines)))
    ]
    read = page_readings(pdf, [p.number for p in wanted], model, ollama_url, cache)
    out: dict[SourceRef, str] = {}
    for page in wanted:
        for k, text in split_lines(page, ocr.latin(read[page.number])).items():
            if SourceRef(page.number, k) in checked:
                out[SourceRef(page.number, k)] = text
    return out
