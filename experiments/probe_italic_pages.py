"""Probe: can a vision decision model tell, from a whole page, whether it has italic words?

Truth from the Gutenberg EPUB's <i>/<em>: each italic phrase, with a few words of
context, is found in the scan's text layer to get its page. A sample of pages
with and without italics goes to the model as one image each, with a yes/no
question.

    uv run python experiments/probe_italic_pages.py work/the-story-of-doctor-dolittle--stokes-1920 \
        work/.cache/gutenberg/501.epub clef-flash:9b [per_class]
"""

import random
import re
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from rapidfuzz import fuzz

from roboscriptorium.book import Book
from roboscriptorium.clients import ollaya
from roboscriptorium.config import Settings
from roboscriptorium.pdf import cached_text_layer, render_png

XHTML = "{http://www.w3.org/1999/xhtml}"
CONTEXT = 4  # words before the italic phrase used to find it in the text layer
MATCH = 90


def norm(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def italic_phrases(epub: Path) -> list[str]:
    """Each italic phrase with a few words before it, from the EPUB's paragraphs."""
    out = []
    with zipfile.ZipFile(epub) as z:
        for name in z.namelist():
            if not name.endswith((".html", ".xhtml")):
                continue
            root = ET.fromstring(z.read(name))
            for p in root.iter(f"{XHTML}p"):
                text = ""
                for node in p.iter():
                    if node.tag in (f"{XHTML}i", f"{XHTML}em") and (node.text or "").strip():
                        before = norm(text).split()[-CONTEXT:]
                        out.append(" ".join([*before, norm("".join(node.itertext()))]))
                    text += node.text or ""
                    text += node.tail or "" if node is not p else ""
    return out


def main() -> None:
    book = Book.load(Path(sys.argv[1]))
    phrases = italic_phrases(Path(sys.argv[2]))
    model = sys.argv[3]
    per_class = int(sys.argv[4]) if len(sys.argv) > 4 else 15
    first, last = book.body_pages
    pages = {
        p.number: norm(" ".join(ln.text for ln in p.lines))
        for p in cached_text_layer(book.source, book.stages / "textlayer.json")
        if first <= p.number <= last and len(p.lines) >= 15
    }
    found: dict[int, list[str]] = {}
    lost = 0
    for phrase in phrases:
        hits = [n for n, text in pages.items() if fuzz.partial_ratio(phrase, text) >= MATCH]
        if len(hits) == 1:
            found.setdefault(hits[0], []).append(phrase)
        else:
            lost += 1
    print(f"{len(phrases)} italic phrases; {sum(map(len, found.values()))} placed on "
          f"{len(found)} pages; {lost} not placed (or ambiguous)")
    random.seed(3)
    italic = random.sample(sorted(found), min(per_class, len(found)))
    plain = random.sample(sorted(set(pages) - set(found)), per_class)

    settings = Settings.from_env()
    client = ollaya.for_model(model, settings.ollaya_url, settings.ollama_url)
    question = {
        "italic": ollaya.noul(
            "This is a page of running text from a printed book. Some words in the running "
            "text on this page are printed in italic type: slanted letters, used for emphasis "
            "or titles."
        )
    }
    rows, t0 = [], time.time()
    for n in italic + plain:
        answer = client.decide({"page": n}, question, image_png=render_png(book.source, n))
        rows.append((n, n in found, answer["italic"].value))
        print(f"  p{n}: italic {n in found!s:5} P(yes) {answer['italic'].value:.2f}  "
              f"{found.get(n, [''])[0][-40:]!r}")
    dt = (time.time() - t0) / len(rows)
    for threshold in (0.3, 0.5, 0.7):
        tp = sum(truth and p >= threshold for _, truth, p in rows)
        fp = sum(not truth and p >= threshold for _, truth, p in rows)
        print(f"P >= {threshold}: italic pages caught {tp}/{len(italic)}, plain pages "
              f"flagged {fp}/{len(plain)}")
    print(f"{model}: {dt:.1f} s per page")


if __name__ == "__main__":
    main()
