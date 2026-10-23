"""Which lines of a page are headings and which are furniture, by the read model from the
page image and its numbered lines: inputs for the line-role trees (`sorter.py`).

On 208 tuning pages (`experiments/probe_page_roles.py --short`) the read model's answer had
4 roles wrong of 5,967 lines against the pipeline's 22, and found all 126 headings against
110 (docs/design.md, "Line roles").
"""

import base64
import hashlib
import json
import re
from pathlib import Path

import httpx
import pymupdf

from roboscriptorium import pagereader
from roboscriptorium.clients.retry import patiently
from roboscriptorium.files import read_cache, write_cache
from roboscriptorium.pdf import PDF_LOCK, PageText

VERSION = 1
MAX_TOKENS = 2000
PROMPT = (
    "This is a page of a printed book. Below is every line read from it, numbered from the "
    "top. Which lines are headings of the book (a chapter, part or section title, name or "
    "number, set where it begins, often larger, spaced, centred or in capitals), and which "
    "are page furniture (a page number, a running head) or stray marks? Every other line is "
    "running text.\n\n{lines}\n\n"
    'Answer with a JSON object and nothing else, for example {{"H": [2], "F": [1, 30]}}.'
)
KINDS = {"H": "heading", "F": "other"}


def listing(page: PageText) -> str:
    return "\n".join(f"{i}. {line.text.strip()}" for i, line in enumerate(page.lines, 1))


def parse(reply: str, count: int) -> dict[int, str] | None:
    """A reply's lines by index from 0, each "heading" or "other"; lines it doesn't name are
    running text. None when it holds no answer."""
    found = re.findall(r"\{[^{}]*\}", reply)
    try:
        answer = json.loads(found[-1]) if found else None
    except json.JSONDecodeError:
        return None
    if not isinstance(answer, dict):
        return None
    out = {}
    for key in ("F", "H"):
        numbers = answer.get(key)
        for n in numbers if isinstance(numbers, list) else []:
            if isinstance(n, int) and 1 <= n <= count:
                out[n - 1] = KINDS[key]
    return out


def ask(png: bytes, text: str, model: str, ollama_url: str) -> str:
    body = {
        "model": model,
        "prompt": PROMPT.format(lines=text),
        "stream": False,
        "think": False,
        "images": [base64.b64encode(png).decode()],
        "options": {"temperature": 0, "num_predict": MAX_TOKENS},
    }

    def generate() -> str:
        resp = httpx.post(f"{ollama_url}/api/generate", json=body, timeout=900)
        resp.raise_for_status()
        return resp.json()["response"]

    return patiently(generate)


def page_roles(
    pdf: Path, pages: list[PageText], model: str, ollama_url: str, cache: Path
) -> dict[int, dict[int, str]]:
    """Per page the model answered for, its heading and furniture lines by index in
    `pages` (the layer with its missing lines added, as the trees see it). A page whose
    reply held no answer is left out. Cached per page under the lines it was shown."""
    kept = read_cache(cache, VERSION, model=model, prompt=PROMPT)
    done: dict[str, dict] = kept["pages"] if kept else {}
    with pymupdf.open(pdf) as doc:
        for page in pages:
            if not page.lines:
                continue
            text = listing(page)
            key = hashlib.sha256(text.encode()).hexdigest()[:16]
            entry = done.get(str(page.number))
            if entry is None or entry["lines"] != key:
                with PDF_LOCK:
                    png = pagereader._render(doc[page.number - 1])
                done[str(page.number)] = {"lines": key, "reply": ask(png, text, model, ollama_url)}
                write_cache(cache, VERSION, {"pages": done}, model=model, prompt=PROMPT)
    out = {}
    for page in pages:
        entry = done.get(str(page.number))
        if entry is not None:
            found = parse(entry["reply"], len(page.lines))
            if found is not None:
                out[page.number] = found
    return out
