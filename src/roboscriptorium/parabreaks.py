"""Paragraph starts the vision judge reads off the page, where the geometry can't tell.

A line may start a paragraph with no indent (a book that sets none, a letter set flush),
and a line set apart (verse, a list, beside a drawn initial) may carry on a paragraph.
The judge sees a line between the lines above and below it, cropped across the text
block, with their text, and says whether it starts a paragraph; where it is at least
`SURE` of it, that answer sets the line's `starts_paragraph` for `reflow`. On 1,383 lines
of tuning pages, the reflow's own calls had 54 wrong starts; the judge's where it was at
least 0.7 sure left 17, and broke none it had right (`experiments/probe_break_judge.py`,
2026-10-17).

A line can't start a paragraph after a line that doesn't end a sentence when it begins
in lower case (2 such starts among 3,800 lines, both after a scrap): it carries on, and
isn't asked.
"""

import re
from dataclasses import replace

import pymupdf

from roboscriptorium.clients import decide
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import PDF_LOCK, PageText
from roboscriptorium.roles import DecisionCache, LineRole, is_body

SURE = 0.7
DPI = 150
PAD = 6  # points beside the text block
GAP = 4  # points above the line above and below the line below
QUESTION = {
    "start": decide.choice(
        "The image is cut from a printed book page: the line in question with the line "
        "above it and the line below it. Does the line in question start a new paragraph, "
        "or does it carry on the paragraph of the line above? Look at its indent, the "
        "white space above it and the length of the line above, and at what the words say "
        "(a new speaker, a letter's greeting, a heading of a list).",
        {
            "starts": "the line in question starts a new paragraph",
            "continues": "the line in question carries on the paragraph of the line above",
        },
    )
}
_ENDS = re.compile(r"[.!?…:;’”'\")\]]\s*$")


def can_start(above: str, text: str) -> bool:
    """Whether a line can start a paragraph after `above`: it ends a sentence, there is
    none, or the line doesn't begin in lower case."""
    return not above.strip() or bool(_ENDS.search(above)) or not text.lstrip()[:1].islower()


def judged(
    pdf,
    pages: list[PageText],
    roles: dict[SourceRef, LineRole] | None,
    client,
    cache: DecisionCache,
) -> list[PageText]:
    """Copies of `pages` with `starts_paragraph` set on the body lines the judge is sure of,
    and to False on body lines that can't start one. A line that has it set already (an
    answer) keeps it."""
    out = []
    before = ""
    with PDF_LOCK, pymupdf.open(pdf) as doc:
        for page in pages:
            lines = list(page.lines)
            for k, line in enumerate(page.lines):
                above = page.lines[k - 1].text if k else before
                body = roles is None or is_body(roles.get(SourceRef(page.number, k)))
                if not body or line.starts_paragraph is not None or not line.text.strip():
                    continue
                if not can_start(above, line.text):
                    lines[k] = replace(line, starts_paragraph=False)
                    continue
                below = page.lines[k + 1].text if k + 1 < len(page.lines) else ""
                state = {
                    "line above" + ("" if k else " (the last line of the page before)"): above,
                    "line in question": line.text,
                    "line below": below,
                }
                where = {"page": page.number, "line": k, "crop": [DPI, PAD, GAP]}
                answer = _ask(client, cache, state, where, lambda p=page, i=k: _crop(doc, p, i))
                if answer["confidence"] >= SURE:
                    lines[k] = replace(line, starts_paragraph=answer["value"] == "starts")
            if page.lines:
                before = page.lines[-1].text
            out.append(replace(page, lines=lines))
    return out


def _ask(client, cache: DecisionCache, state: dict, where: dict, image) -> dict:
    """The judge's answer, cached on the state and on `where` the crop comes from."""
    key = DecisionCache.key(client.model, QUESTION, {**state, **where})
    answer = cache.get(key)
    if answer is None:
        a = client.decide(state, QUESTION, image_png=image())["start"]
        answer = {"value": a.value, "confidence": a.confidence}
        cache.put(key, answer)
    return answer


def _crop(doc: pymupdf.Document, page: PageText, k: int) -> bytes:
    lines = page.lines
    left = min(ln.x0 for ln in lines) - PAD
    right = max(ln.x1 for ln in lines) + PAD
    top = lines[max(0, k - 1)].y0 - GAP
    bottom = lines[min(len(lines) - 1, k + 1)].y1 + GAP
    clip = pymupdf.Rect(left, top, right, bottom)
    return doc[page.number - 1].get_pixmap(dpi=DPI, clip=clip).tobytes("png")
