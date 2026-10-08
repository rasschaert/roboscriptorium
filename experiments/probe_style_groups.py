"""Probe: ask the role model about a whole group of lines set alike, not line by line.

Display lines (larger than the body text, or in capitals) set alike in one place on
their pages are gathered as `roles._heading_styles` does; the model sees the
group's lines with their pages, the type, the place and how many open a sunk page.

    uv run python experiments/probe_style_groups.py work/<book> [--pages 9-64]
"""

import argparse
import json
from pathlib import Path

from roboscriptorium import pipeline, roles, typestyle
from roboscriptorium.book import Book
from roboscriptorium.clients import decide
from roboscriptorium.config import Settings
from roboscriptorium.page import sunk_pages

ap = argparse.ArgumentParser()
ap.add_argument("book")
ap.add_argument("--pages")
ap.add_argument("--out")
args = ap.parse_args()
book = Book.load(Path(args.book))
span = tuple(map(int, args.pages.split("-"))) if args.pages else None

captured = {}
original = roles._heading_styles


def capture(pages, answers, styles, repeated):
    captured.update(pages=pages, answers=dict(answers), styles=styles, repeated=repeated)
    return original(pages, answers, styles, repeated)


roles._heading_styles = capture
stages = pipeline.run(book, pages=span)
pages, answers, styles, repeated = (captured[k] for k in ("pages", "answers", "styles", "repeated"))
lines = {roles.SourceRef(p.number, i): ln for p in pages for i, ln in enumerate(p.lines)}
places = {
    roles.SourceRef(p.number, i): "top"
    if i < roles.SUNK_HEADING_LINES
    else "foot"
    if i >= len(p.lines) - roles.EDGE_LINES_BOTTOM
    else "middle"
    for p in pages
    for i in range(len(p.lines))
}
voters = {
    ref: styles[ref]
    for ref, role in answers.items()
    if typestyle.display(styles.get(ref))
    and not roles._is_body(role)
    and not roles.garbled(lines[ref])
    and repeated[ref] < roles.HEADING_MAX_REPEATS
}
sunk = sunk_pages(pages)
PLACES = {"top": "among the first lines of their pages", "foot": "at the foot of their pages",
          "middle": "in the middle of their pages"}
GROUP_ROLES = {
    "chapter_heading": "Chapter or part headings: each appears once, where a chapter or part "
    "begins, such as a number, a numeral, 'CHAPTER XII.', 'Proloog' or a title",
    "running_head": "The book or chapter title repeated at the top of pages",
    "page_number": "Page numbers",
    "artifact": "Not part of the book's text: stamps, printer's marks or scanning noise",
    "body": "Lines of the running text that happen to be short",
}
QUESTION = {"role": decide.choice(
    "These lines come from different pages of a printed book. They are set in the same type "
    "and sit in the same place on their pages. What are they?", GROUP_ROLES)}
settings = Settings.from_env()
client = decide.for_model(settings.role_model, settings.ollama_url)
out = []
for group in typestyle.groups(voters, places):
    if len(group) < 2:
        continue
    group.sort(key=lambda r: (r.page, r.line))
    st = styles[group[0]]
    size = sorted(styles[r].size for r in group)[len(group) // 2]
    kind = f"{size:.1f}× the size of the body text" + (", in capitals" if st.capitals else "")
    state = {
        "lines": [f"page {r.page}: {lines[r].text}" for r in group[:30]],
        "count": len(group),
        "type": kind,
        "place": PLACES[places[group[0]]],
        "on_pages_where_the_text_starts_lower_than_usual": f"{sum(r.page in sunk for r in group)} "
        f"of {len(group)}",
    }
    a = client.decide(state, QUESTION)["role"]
    model = [answers[r].role for r in group]
    print(f"-- {len(group)} lines, {kind}, {places[group[0]]}: {a.value} {a.confidence:.2f}"
          f" {json.dumps({k: round(v, 2) for k, v in a.probabilities.items()})}")
    for r in group[:8]:
        print(f"   p{r.page} {answers[r].role:16} {lines[r].text[:50]!r}")
    out.append({"state": state, "answer": a.value, "probabilities": a.probabilities,
                "line_roles": model})
if args.out:
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1))
