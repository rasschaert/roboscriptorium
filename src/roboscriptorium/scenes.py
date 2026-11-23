"""Scene breaks lost at a page turn, found from the text and asked of the reviewer.

A scene break at the top of a page leaves no trace when the page before ends a sentence
on a full line and the next opens flush: the white space fell at the foot of the page,
and the geometry is a paragraph running on. Only the words can tell. At each such turn
the build sets no break at (a sentence ends before it, the next page opens on the
margin of a book that indents its paragraphs, no chapter starts there), a decision
model reads the lines on either side and says whether a new scene starts, a letter or
other document set into the story begins, or the same scene goes on. Where a new scene
is at least `ASK_AT` likely, the line is a question for the reviewer ("scene" in
`flags.REASONS`); the answer "scene" sets the break (`Line.scene`). Nothing is set without
an answer.

On the tuning books' 165 such turns, 18 of them scene breaks, Shisa DE-1 at 0.5 finds 10
with 4 false; at 0.7 it finds 2 (`experiments/probe_scene_turns.py`, decisions.md,
2026-11-24). Without the letter answer it took letters and diary entries for scenes (25
false at 0.5).
"""

import re

from roboscriptorium.clients import decide
from roboscriptorium.ir import Heading, Paragraph, SourceRef
from roboscriptorium.pdf import PageText
from roboscriptorium.roles import DecisionCache

ASK_AT = 0.5
AROUND = 6  # lines shown on either side of the turn
# The next page's first line sits this close to its page's margin, in points: left of it
# by the layer's slip, right of it by less than an indent.
FLUSH_LEFT = 2.5
FLUSH_RIGHT = 3.5
# The text before the turn ends a sentence: a stop, ! ? or ellipsis, perhaps closing quotes.
ENDS = re.compile(r"[.!?…][’”»\"')\]]*\s*$")
QUESTION = {
    "scene": decide.choice(
        "A page of a printed novel ends and the next page begins. Does a new scene start at "
        "the top of the next page (a jump in time, place or point of view, which the book "
        "marks with a blank line or an ornament), or does the same scene go on?",
        {
            "new_scene": "a new scene of the story starts at the top of the next page",
            "document": "a letter, diary entry, dated note or other document set into the "
            "story begins",
            "continues": "the same scene goes on across the page turn",
        },
    )
}


def turns(
    pages: list[PageText], blocks: list, indented: bool
) -> list[tuple[SourceRef, SourceRef, dict]]:
    """The page turns a scene break may hide at, each as the next page's first line, the
    last line of the page before and the question's state. `blocks` are reflowed from
    `pages` (the review's lines); `indented` says whether the book indents its paragraphs
    (`parabreaks.indents`)."""
    if not indented:
        return []
    by_number = {p.number: p for p in pages}
    order: list[tuple[int, SourceRef]] = []
    for k, b in enumerate(blocks):
        if isinstance(b, Paragraph) and not (b.epigraph or b.dedication or b.item):
            order += [(k, s) for s in b.sources if not s.typed and s.page in by_number]

    def text(s: SourceRef) -> str:
        return by_number[s.page].lines[s.line].text

    out = []
    for i in range(1, len(order)):
        (k, s), (kp, prev) = order[i], order[i - 1]
        if s.page == prev.page or not ENDS.search(text(prev)):
            continue
        block = blocks[k]
        if k != kp and (
            block.break_before
            or block.opening
            or any(isinstance(b, Heading) for b in blocks[kp + 1 : k])
        ):
            continue  # the build sets a break or a chapter opens here
        body = [by_number[s.page].lines[t.line] for _, t in order if t.page == s.page]
        margin = sorted(ln.x0 for ln in body)[len(body) // 4]
        if not -FLUSH_LEFT <= by_number[s.page].lines[s.line].x0 - margin <= FLUSH_RIGHT:
            continue
        out.append(
            (
                SourceRef(s.page, s.line),
                SourceRef(prev.page, prev.line),
                {
                    "end of the page before": "\n".join(
                        text(t) for _, t in order[max(0, i - AROUND) : i]
                    ),
                    "start of the next page": "\n".join(text(t) for _, t in order[i : i + AROUND]),
                },
            )
        )
    return out


def asked(
    pages: list[PageText],
    blocks: list,
    indented: bool,
    language: str,
    client,
    cache: DecisionCache,
) -> dict[SourceRef, tuple[float, SourceRef]]:
    """The lines to ask whether a scene opens at, each with the model's probability that
    one does and the last line of the page before: each turn (`turns`) where it is at
    least `ASK_AT`. Each answer is cached as it comes."""
    out = {}
    for ref, before, where in turns(pages, blocks, indented):
        state = {"language of the book": language, **where}
        key = DecisionCache.key(client.model, QUESTION, state)
        answer = cache.get(key)
        if answer is None:
            a = client.decide(state, QUESTION)["scene"]
            answer = {"value": a.value, "probabilities": a.probabilities}
            cache.put(key, answer)
        p = answer["probabilities"].get("new_scene", 0.0)
        if p >= ASK_AT:
            out[ref] = (p, before)
    return out
