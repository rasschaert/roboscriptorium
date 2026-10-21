"""A book's setup drafted from its PDF alone (`roboscriptorium init`).

What the tool can tell without being told: the language (which word list knows more of the
text's words), each page's kind and so the two ends of the text proper (`pagekinds`), the cover,
and the lines of the title page. Everything else is left for a person, and the two ends are
always shown for confirmation: a page too many is mild, a page cut is not.

A page is named by both its numbers wherever it is shown (`pagekinds.page_label`): the PDF's own
page, which `book.toml` and every `--pages` use, and the number the page prints.
"""

import base64
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image, ImageDraw

from roboscriptorium import pagekinds
from roboscriptorium.lexicon import Lexicon
from roboscriptorium.pdf import PageText, render_png

# How many pages are shown on each side of an end.
AROUND = 2
# Words of the text sampled to tell the language.
SAMPLE = 20_000
FRONT_PROMPT = (
    "These are two pages of a scanned book: its title page and its copyright page (the images, "
    "in that order). Answer with one JSON object and nothing else, with the keys title (the "
    "book's title as printed on the title page, without the author), author (the author's name "
    "as printed, in the usual order, first name first) and translator (the translator's name "
    "if the pages name one, else an empty string)."
)


@dataclass
class Draft:
    name: str
    pages: list[PageText]
    kinds: dict[int, str]
    offset: int | None
    language: str
    shares: dict[str, float]
    cover: int | None
    first: int
    last: int
    title_lines: list[str]
    front: dict[str, str] = field(default_factory=dict)


def slug(stem: str) -> str:
    """A folder name for a book from its file's name."""
    return re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-") or "book"


def language_of(
    pages: list[PageText], lexicons: dict[str, Lexicon] | None = None
) -> tuple[str, dict[str, float]]:
    """The language whose word list knows the larger share of the text's words, and each share."""
    lexicons = lexicons or {"nl": Lexicon.load("nld"), "en": Lexicon.load("eng")}
    words = [
        w for p in pages for ln in p.lines for w in re.findall(r"[a-zà-ÿ]{3,}", ln.text.lower())
    ]
    sample = words[:: max(1, len(words) // SAMPLE)]
    shares = {
        code: sum(lex.knows(w) for w in sample) / max(1, len(sample))
        for code, lex in lexicons.items()
    }
    return max(shares, key=shares.get), shares


def title_lines(pages: list[PageText], kinds: dict[int, str]) -> list[str]:
    """The lines of the title page (else the half title): the author, the title, the publisher."""
    for kind in ("title", "half-title"):
        for p in pages:
            if kinds.get(p.number) == kind:
                return [ln.text.strip() for ln in p.lines if ln.text.strip()][:6]
    return []


def parse_front(text: str) -> dict[str, str]:
    """The title, author and translator in a model's JSON answer; empty where it isn't JSON."""
    try:
        got = json.loads(re.search(r"\{.*\}", text, re.S).group())
    except (AttributeError, json.JSONDecodeError):
        return {}
    return {
        k: got[k].strip() for k in ("title", "author", "translator") if isinstance(got.get(k), str)
    }


def front_pages(kinds: dict[int, str]) -> list[int]:
    """The title page (else the half title) and the copyright page, those the book has."""
    pick = lambda *names: next((n for n, k in sorted(kinds.items()) if k in names), None)  # noqa: E731
    return [n for n in (pick("title") or pick("half-title"), pick("colophon")) if n]


def read_front(pdf: Path, kinds: dict[int, str], model: str, url: str) -> dict[str, str]:
    """The title, author and translator the read model finds on the title and copyright pages."""
    pages = front_pages(kinds)
    if not pages:
        return {}
    images = [base64.b64encode(render_png(pdf, n, max_pixels=1_000_000)).decode() for n in pages]
    body = {"model": model, "prompt": FRONT_PROMPT, "images": images, "stream": False,
            "think": False, "options": {"temperature": 0, "num_predict": 300}}  # fmt: skip
    resp = httpx.post(f"{url}/api/generate", json=body, timeout=600)
    resp.raise_for_status()
    return parse_front(resp.json()["response"])


def draft(name: str, pages: list[PageText], kinds: dict[int, str], lexicons=None) -> Draft:
    """The draft of a book from its text layer and its pages' kinds."""
    language, shares = language_of(pages, lexicons)
    first, last = pagekinds.ends(kinds)
    cover = next((n for n, k in sorted(kinds.items()) if k == "cover"), None)
    return Draft(
        name, pages, kinds, pagekinds.printed_offset(pages), language, shares, cover, first, last,
        title_lines(pages, kinds),
    )  # fmt: skip


def _q(text: str) -> str:
    """Text safe inside a TOML basic string."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _shares(d: Draft) -> str:
    """The share of the text's words each language's word list knows, the larger first."""
    ranked = sorted(d.shares.items(), key=lambda t: -t[1])
    return ", ".join(f"{share:.0%} as {code}" for code, share in ranked)


def toml(d: Draft) -> str:
    """The draft book.toml: every line to confirm says so, and both ends name both numbers."""
    shares = _shares(d)
    first = pagekinds.page_label(d.first, d.offset)
    last = pagekinds.page_label(d.last, d.offset)
    seen = "; ".join(d.title_lines) or "none found"
    translator = (
        f'translator = "{_q(d.front["translator"])}"   # confirm: the copyright page names them\n'
        if d.front.get("translator")
        else ""
    )
    return f"""# Drafted by `roboscriptorium init` from the PDF alone. Confirm what is marked.
title = "{_q(d.front.get("title", ""))}"   # confirm. On the title page: {seen}
author = "{_q(d.front.get("author", ""))}"   # confirm
{translator}language = "{d.language}"   # confirm. The word lists know {shares} of the text's words
cover_page = {d.cover or 1}
# The text proper, as PDF pages (what body_pages and --pages take). Confirm both ends:
#   first: {first}
#   last:  {last}
body_pages = [{d.first}, {d.last}]
"""


def report(d: Draft) -> str:
    """What `init` found, for a person to confirm: the two ends with the pages around them."""
    counts = Counter(d.kinds.values())
    lines = [
        f"# {d.name}: what `init` found",
        "",
        f"{len(d.pages)} PDF pages. Language: {d.language} (the word lists know {_shares(d)}).",
        "",
        "## The text proper: confirm both ends",
        "",
        f"- **First page:** {pagekinds.page_label(d.first, d.offset)}",
        f"- **Last page:** {pagekinds.page_label(d.last, d.offset)}",
        "",
        "A page too many at an end pads the book, a page too few cuts it: look at the pages",
        "around each end (`init/ends.png`), then edit `body_pages` in `book.toml` if one is off.",
        "",
    ]
    for label, end in (("First end", d.first), ("Last end", d.last)):
        lines += [f"### {label}", "", "| Page | Kind | In the book |", "| --- | --- | --- |"]
        for n in _around(d, end):
            mark = "yes" if pagekinds.fate(d.kinds[n]) == "in" else "no"
            here = " **← the end**" if n == end else ""
            lines.append(f"| {pagekinds.page_label(n, d.offset)}{here} | {d.kinds[n]} | {mark} |")
        lines.append("")
    lines += [
        "## Also drafted",
        "",
        f"- Cover: PDF page {d.cover or 1}.",
        f"- On the title page: {'; '.join(d.title_lines) or 'no title page found'}.",
        f"- Read from the title and copyright pages (confirm): {_front(d)}.",
        f"- Kinds found: {', '.join(f'{k} {n}' for k, n in counts.most_common())}.",
        "",
    ]
    return "\n".join(lines)


def _front(d: Draft) -> str:
    got = [f"{k} {v!r}" for k, v in d.front.items() if v]
    return ", ".join(got) or "nothing; title and author are left for you"


def _around(d: Draft, end: int) -> list[int]:
    return [n for n in range(end - AROUND, end + AROUND + 1) if n in d.kinds]


def sheet(pdf: Path, d: Draft, path: Path, height: int = 420) -> None:
    """A contact sheet of the pages around both ends, each captioned with both its numbers."""
    shown = [_around(d, d.first), _around(d, d.last)]
    thumbs = []
    for row in shown:
        for n in row:
            im = Image.open(BytesIO(render_png(pdf, n, max_pixels=200_000))).convert("RGB")
            im = im.resize((max(1, int(im.width * height / im.height)), height))
            thumbs.append((n, im))
    cell = max(im.width for _, im in thumbs) + 8
    caption = 34
    columns = max(len(r) for r in shown)
    sheet_im = Image.new("RGB", (cell * columns, (height + caption) * len(shown)), "white")
    draw = ImageDraw.Draw(sheet_im)
    it = iter(thumbs)
    for r, row in enumerate(shown):
        for c, _ in enumerate(row):
            n, im = next(it)
            x, y = c * cell + 4, r * (height + caption)
            sheet_im.paste(im, (x, y))
            end = d.first if r == 0 else d.last
            draw.text((x, y + height + 2), f"PDF {n}{' (end)' if n == end else ''}", fill="black")
            draw.text(
                (x, y + height + 16),
                pagekinds.page_label(n, d.offset).split("(")[1].rstrip(")"),
                fill="black",
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet_im.save(path)
