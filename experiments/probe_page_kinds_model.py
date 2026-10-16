"""Probe: the sorter's page-kind question on the hand-labelled pages, for `init`.

Asks a decision model (clef-flash by default) each labelled page's kind, with the page
image and what the text layer says about it (its words, its first lines, its place in
the book), and scores the answers against `tryouts/page-kinds-v1.json` the way
`probe_page_signals.py --score` does: per page, by what becomes of it, and the ends of
the text proper. Answers are cached per model and question in
work/probes/page-kinds/answers-<model>.json, so a rerun only asks what is new.

    uv run python experiments/probe_page_kinds_model.py [model] [--books a,b]

~1,000 pages, about 4 s each on clef-flash: an hour.
"""

import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from probe_page_signals import ends, fate, layer  # noqa: E402

from roboscriptorium.clients import decide  # noqa: E402
from roboscriptorium.files import write_atomic  # noqa: E402
from roboscriptorium.pdf import render_png  # noqa: E402

KINDS = {
    "cover": "the front cover",
    "back-cover": "the back cover, with or without a blurb",
    "blank": "an empty page, maybe with show-through or a lone page number",
    "scan-noise": "a digitisation notice (Internet Archive's stamp page) or a colour card",
    "library": "library stamps, barcode, due-date slip, card pocket, handwriting only",
    "endpaper": "an endpaper, the inside of a cover or a jacket flap",
    "half-title": "the book's title alone, before the title page",
    "title": "the title page: title, author, publisher",
    "colophon": "the copyright page: ©, ISBN, printer, original title, translator credit",
    "contents": "a table of contents",
    "also-by": "a list of the author's other books",
    "ads": "advertisements for other books or products, praise for other books",
    "praise": "praise for this book: quotes from reviews",
    "dedication": "a dedication ('Voor ...', 'For ...')",
    "motto": "a motto or epigraph: a short quotation set apart, with its source",
    "dramatis-personae": "a list of characters, a map, a family tree",
    "foreword": "a foreword, preface or introduction before the text",
    "part-title": "a page with only a part heading ('Deel een', 'Part II', a lone numeral)",
    "text": "running text: a chapter, prologue or epilogue, its opening or its last lines",
    "plate": "a full-page picture, a frontispiece or plate",
    "afterword": "an afterword or author's note after the text",
    "notes": "endnotes",
    "appendix": "an appendix, bibliography or list of sources",
    "acknowledgements": "acknowledgements, thanks",
    "about-author": "about the author: a short biography, an author photo",
    "index": "a back-of-book index",
}
QUESTION = {
    "kind": decide.choice(
        "This is a scanned page of a printed book. What kind of page is it? Use the page "
        "image first; the text layer may be missing or garbled.",
        KINDS,
    )
}
TAG = hashlib.sha1(json.dumps(QUESTION, sort_keys=True).encode()).hexdigest()[:8]


def state(book: str, n: int, total: int, page) -> dict:
    lines = [ln.text for ln in page.lines if ln.text.strip()]
    return {
        "book": book,
        "page": f"{n} of {total}",
        "words_on_page": sum(len(t.split()) for t in lines),
        "first_lines": lines[:6],
        "last_lines": lines[-2:] if len(lines) > 6 else [],
    }


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    model = args[0] if args else "clef-flash:9b"
    only = None
    if "--books" in sys.argv:
        only = set(sys.argv[sys.argv.index("--books") + 1].split(","))
    labels = json.loads(Path("tryouts/page-kinds-v1.json").read_text())["books"]
    # A retired pair's scan is deleted from work/ (decisions.md); its labels stay valid.
    gone = [n for n in labels if not (Path("work") / n / "source.pdf").exists()]
    for name in gone:
        print(f"skipped {name}: no work/{name}/source.pdf")
    labels = {n: e for n, e in labels.items() if n not in gone}
    cache_path = Path("work/probes/page-kinds") / f"answers-{model.replace(':', '_')}-{TAG}.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    client = decide.for_model(model, "http://127.0.0.1:11434")
    fates: Counter = Counter()
    kinds_right = Counter()
    ends_right = Counter()
    confusions: Counter = Counter()
    started, asked = time.time(), 0
    for name, entry in labels.items():
        if only and name not in only:
            continue
        book = Path("work") / name
        pages = layer(book)
        total = len(pages)
        want = {int(k): v for k, v in entry["pages"].items()}
        got = {}
        for n, kind in sorted(want.items()):
            key = f"{name}:{n}"
            if key not in cache:
                answer = client.decide(
                    state(name, n, total, pages[n - 1]), QUESTION, image_png=render_png(book / "source.pdf", n)
                )["kind"]
                cache[key] = [answer.value, round(answer.confidence, 3)]
                asked += 1
                if asked % 25 == 0:
                    write_atomic(cache_path, json.dumps(cache))
                    rate = (time.time() - started) / asked
                    print(f"  {asked} asked, {rate:.1f} s a page", flush=True)
            got[n] = cache[key][0]
            kinds_right[got[n] == kind] += 1
            fates[(fate(kind), fate(got[n]))] += 1
            if fate(got[n]) != fate(kind):
                confusions[(kind, got[n])] += 1
        full_want = {p.number: want.get(p.number, "text") for p in pages}
        full_got = {p.number: got.get(p.number, "text") for p in pages}
        w, g = ends(full_want), ends(full_got)
        ends_right["first"] += w[0] == g[0]
        ends_right["last"] += w[1] == g[1]
        ends_right["books"] += 1
        if w != g:
            print(f"  {name}: text proper {w[0]}–{w[1]}, asked {g[0]}–{g[1]}")
    write_atomic(cache_path, json.dumps(cache))
    print(f"{model}: kind right {kinds_right[True]}/{sum(kinds_right.values())}")
    print("fate (labelled, answered):", dict(fates))
    print("ends right:", dict(ends_right))
    for (kind, g), n in confusions.most_common(20):
        print(f"  {n:4}  {kind:18} → {g}")


if __name__ == "__main__":
    main()
