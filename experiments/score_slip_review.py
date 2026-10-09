"""Score a slip review: each answer against the golden reference, picks and typed lines
apart, and how often the offered readings held the right line.

The review's questions come from its running server (`/api/state`), the truth per line
from `golden.align` on the text layer with the missing lines added, as the review saw it.

    uv run python experiments/score_slip_review.py <book dir> <golden scan dir> <pages> <chapters> [port]
"""

import json
import sys
from pathlib import Path

import httpx
from ocr_trust_data import fold

from roboscriptorium import layout, missing
from roboscriptorium.book import Book
from roboscriptorium.cli import _range, _verdicts
from roboscriptorium.config import Settings
from roboscriptorium.corrections import place
from roboscriptorium.disagreements import patch
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.ir import SourceRef
from roboscriptorium.ocrcheck import differences
from roboscriptorium.pdf import cached_text_layer


def main() -> None:
    book_dir, golden_dir, pages, chapters = sys.argv[1:5]
    port = sys.argv[5] if len(sys.argv) > 5 else "8766"
    book = Book.load(Path(book_dir))
    first, last = _range(pages)
    layer = cached_text_layer(book.source, book.stages / "textlayer.json")
    body = [p for p in layer if first <= p.number <= last]
    regions = layout.detect(book.source, [p.number for p in body], book.stages / "layout.json")
    found = missing.candidates(body, regions, {})
    s = Settings.from_env()
    read = missing.read(book.source, found, s.ocr_model, s.ollama_url, book.stages / "missing-lines.json")
    body = missing.add(body, found, read)
    a, b = _range(chapters)
    reference = load_chapters(Golden.load(book.golden).text_dir)[a - 1 : b]
    reference, _ = patch(reference, _verdicts(Book.load(Path(golden_dir))))
    truth = align(body, reference)
    lines = {p.number: p.lines for p in body}

    items = httpx.get(f"http://127.0.0.1:{port}/api/state", timeout=30).json()["items"]
    rows = []
    for it in items:
        ans = it.get("answer")
        if not ans:
            continue
        refs = [SourceRef(it["page"], k) for k in range(it["first"], it["last"] + 1)]
        labels = [truth.get(r) for r in refs]
        roles = {t.role for t in labels if t}
        want = " ".join(t.truth for t in labels if t and t.role != "other")
        readings = [g["text"] for g in it["readings"]]
        got_place = None
        if ans["span"] is not None:
            c = type("C", (), ans)()
            c.span, c.original, c.text, c.joined = tuple(ans["span"]), ans["original"], ans["text"], ans["joined"]
            got_place = place(c)
            # An answer that changed the line outside its place retypes the whole line.
            got = (ans["text"] or ans["original"]) if got_place is None else (
                ans["original"][: c.span[0]] + got_place + ans["original"][c.span[1] :]
            )
            if c.joined and got_place is not None:
                got = ans["text"] or ans["original"]
        else:
            got = ans["text"] if ans["text"] is not None else it["text"]
        got_line = " ".join(got.split("\n")) if ans["action"] in ("text", "heading") else ""
        if ans["action"] in ("drop", "image", "caption", "initial"):
            right = roles <= {"other"}
        elif not want:
            right = False
        elif ans["span"] is not None and got_place is not None:
            # A question about one place is judged at that place: other differences on
            # the line are errors no question asked about.
            a0, a1 = ans["span"]
            end = a0 + len(got_place)
            right = not any(
                d0 < end and a0 < d1 for d0, d1, _, _ in differences(got_line, want)
            ) or fold(got_line) == fold(want)
        else:
            right = fold(got_line) == fold(want)
        if it["readings"]:
            kind = "pick" if any(fold(got_line) == fold(r) for r in readings) else "typed"
        else:
            kind = "role" if ans["text"] is None else "typed"
        def holds(reading: str) -> bool:
            """Whether a reading is right at the question's place (or whole, without one)."""
            if fold(" ".join(reading.split("\n"))) == fold(want):
                return True
            if ans["span"] is None:
                return False
            a0, a1 = ans["span"]
            line = " ".join(reading.split("\n"))
            end = a1 + len(line) - len(ans["original"])
            return not any(d0 < end and a0 < d1 for d0, d1, _, _ in differences(line, want))

        offered = any(holds(r) for r in readings) if readings and want else None
        rows.append((it["key"], it["page"], it["reasons"][0], kind, right, offered, got_line, want))

    for kind in ("pick", "typed", "role"):
        mine = [r for r in rows if r[3] == kind]
        if mine:
            print(f"{kind:6} {sum(r[4] for r in mine)}/{len(mine)} right")
    asked = [r for r in rows if r[5] is not None]
    print(f"offered readings held the right line on {sum(r[5] for r in asked)}/{len(asked)}")
    for key, page, reason, kind, right, offered, got, want in asked:
        if not offered:
            print(f"  no right reading offered: p{page} {reason[:40]} | want {want[:90]!r}")
    print("\nwrong or unverified:")
    for key, page, reason, kind, right, offered, got, want in rows:
        if not right:
            print(f"  p{page} {reason} {kind} offered-right={offered}\n    got  {got[:110]!r}\n    want {want[:110]!r}")
    out = Path(book_dir) / "review" / "slip-score.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
