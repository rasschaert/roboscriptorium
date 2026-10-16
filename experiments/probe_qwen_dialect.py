"""Does telling the read model to keep the author's own spelling stop it standardising?

Qwen reads Ex-minnaar's Flemish into standard Dutch ("wijveke" → "wijfje", "bezeikt" →
"bezocht"). The labelled set: the book's answered suspects where Qwen alone read
different letters from the layer (the reviewer said which was printed). Each line is
read again with the book's prompt plus `KEEP`, cached in work/probes/qwen-dialect/,
and scored: how often Qwen's reading now matches the reviewer's line where it used to
be wrong, and still matches where it was right.

    uv run python experiments/probe_qwen_dialect.py work/ex-minnaar
"""

import json
import sys
from pathlib import Path

from roboscriptorium import corrections, ocr, pipeline, trust, trustdata
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.corrections import Corrections
from roboscriptorium.ir import SourceRef

KEEP = (
    " Keep the author's own spelling exactly as printed, even where it is dialect, slang"
    " or unusual: never change a word to its standard form."
)


def main(book_dir: str) -> None:
    book = Book.load(Path(book_dir))
    settings = Settings.from_env()
    raw = json.loads((book.stages / "ocr-check.json").read_text())
    suspects = [trustdata.suspect({"suspect": s}) for s in raw]
    answers = Corrections(book.corrections_path)
    rows = [
        r
        for r in trust.rows_from(suspects, corrections.answered(answers, suspects))
        if r["settled"]
    ]
    picked = []
    for r in rows:
        s = r["suspect"]
        for k in range(1, 1 + len(s["others"])):
            kind, readers = trust._bucket(s, k)
            if kind == "letters" and readers == ("qwen",):
                picked.append((r, k))
    print(f"{len(picked)} answered places where Qwen alone read other letters")
    lang = ocr.language(book.language)
    layer = pipeline.cached_text_layer(book.source, book.stages / "textlayer.json", lang)
    whole = [p for p in layer if book.body_pages[0] <= p.number <= book.body_pages[1]]
    style = pipeline.dash_style(book, whole)
    dots = pipeline.ellipsis_style(book, whole)
    prompt = pipeline.read_prompt(book, whole, style, dots) + KEEP
    pages = {p.number: p for p in layer}
    checked = {}
    for r, k in picked:
        s = r["suspect"]
        page = pages[s["page"]]
        at = [i for i, ln in enumerate(page.lines) if ln.text == s["original"]]
        if at:
            checked[(r["suspect"]["page"], at[0])] = (r, k)
    wanted = sorted({p for p, _ in checked})
    got = readers.line_readings(
        book.source,
        [pages[n] for n in wanted],
        {SourceRef(p, i) for p, i in checked},
        settings.read_model,
        settings.ollama_url,
        Path("work/probes/qwen-dialect") / f"{book.root.name}.json",
        prompt,
    )
    fixed = kept = broke = still = 0
    for (p, i), (r, k) in checked.items():
        s = r["suspect"]
        new = got[SourceRef(p, i)]
        was_right = r["right"][k]
        versions = [s["ours"], *s["others"]]
        printed = [v for v, ok in zip(versions, r["right"], strict=True) if ok]
        # Right at the place: it reads a printed version there and not this wrong one.
        now_right = any(v in new for v in printed) and (
            was_right or versions[k] in printed[0] or versions[k] not in new
        )
        if was_right:
            kept += now_right
            broke += not now_right
        else:
            fixed += now_right
            still += not now_right
        mark = "ok " if now_right else "   "
        print(f"  {mark}p{p} was {s['others'][k - 1]!r} (right: {was_right}) now {new!r}")
    print(f"was wrong: {fixed} now right, {still} still wrong; was right: {kept} kept, {broke} lost")


if __name__ == "__main__":
    main(sys.argv[1])
