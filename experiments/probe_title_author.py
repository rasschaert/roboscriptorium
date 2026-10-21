"""Title, author and translator from the title page and the copyright page, for `init`: the read
model is shown both pages of a scan and asked for them as JSON; scored against each book's own
`book.toml` (title, author, translator), after folding case, accents and punctuation.

    uv run python experiments/probe_title_author.py [limit]

The pages are the ones `tryouts/page-kinds-v1.json` labels title (else half-title) and colophon.
Answers are cached in work/probes/title-author/<book>.json. About 15 s a book.
"""

import base64
import json
import re
import sys
import tomllib
import unicodedata
from pathlib import Path

import httpx

from roboscriptorium.config import Settings
from roboscriptorium.files import write_atomic
from roboscriptorium.pdf import render_png

CACHE = Path("work/probes/title-author")
PROMPT = (
    "These are two pages of a scanned book: its title page and its copyright page (the images, "
    "in that order). Answer with one JSON object and nothing else, with the keys title (the book's "
    "title as printed on the title page, without the author), author (the author's name as printed, "
    "in the usual order, first name first), translator (the translator's name if the pages name one, "
    "else an empty string) and language (nl or en, the language of the book's text)."
)


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in text if not unicodedata.combining(c))).strip()


def pages_of(entry: dict) -> list[int]:
    kinds = {int(k): v for k, v in entry["pages"].items()}
    title = next((n for n, k in sorted(kinds.items()) if k == "title"), None) or next(
        (n for n, k in sorted(kinds.items()) if k == "half-title"), None
    )
    colophon = next((n for n, k in sorted(kinds.items()) if k == "colophon"), None)
    return [n for n in (title, colophon) if n]


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    settings = Settings.from_env()
    labels = json.loads(Path("tryouts/page-kinds-v1.json").read_text())["books"]
    CACHE.mkdir(parents=True, exist_ok=True)
    right = {"title": 0, "author": 0, "translator": 0, "language": 0}
    total = 0
    for name, entry in sorted(labels.items())[: limit or None]:
        root = Path("work") / name
        if not (root / "source.pdf").exists() or not (root / "book.toml").exists():
            continue
        want = tomllib.loads((root / "book.toml").read_text())
        pages = pages_of(entry)
        cache = CACHE / f"{name}.json"
        if cache.exists():
            got = json.loads(cache.read_text())
        else:
            images = [base64.b64encode(render_png(root / "source.pdf", n, max_pixels=1_000_000)).decode() for n in pages]
            body = {"model": settings.read_model, "prompt": PROMPT, "images": images, "stream": False, "think": False,
                    "options": {"temperature": 0, "num_predict": 300}}
            resp = httpx.post(f"{settings.ollama_url}/api/generate", json=body, timeout=600)
            resp.raise_for_status()
            text = resp.json()["response"]
            try:
                got = json.loads(re.search(r"\{.*\}", text, re.S).group())
            except (AttributeError, json.JSONDecodeError):
                got = {}
            write_atomic(cache, json.dumps(got, ensure_ascii=False))
        total += 1
        marks = {
            "title": fold(got.get("title", "")) == fold(want["title"]),
            "author": fold(got.get("author", "")) == fold(want["author"]),
            "translator": fold(got.get("translator", "")) == fold(want.get("translator", "")),
            "language": got.get("language", "") == want["language"],
        }
        for k, ok in marks.items():
            right[k] += ok
        wrong = [k for k, ok in marks.items() if not ok]
        print(f"{name[:34]:34} pages {pages}  " + ("all right" if not wrong else "wrong: " + ", ".join(
            f"{k} ({got.get(k, '')!r} for {want.get(k, '')!r})" for k in wrong)), flush=True)
    print(f"{total} books; right:", right)
