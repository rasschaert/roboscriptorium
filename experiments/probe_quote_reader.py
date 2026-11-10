"""The quote check as a reader of the OCR check (`ROBO_QUOTE_READER`), off and on, on
copies of built books: what it fixes, keeps and asks, and the quote questions left.

    uv run python experiments/probe_quote_reader.py <book>[:first-last] …

Each book's folder is copied to work/probes/quote-reader/<book> (its caches with it), so
the book's own build and review stay as they are. Results in <book>.json beside it.
"""

import json
import shutil
import sys
from dataclasses import asdict, replace
from pathlib import Path

from roboscriptorium import ocrdoubts, pipeline, quotes
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.ir import Paragraph

OUT = Path("work/probes/quote-reader")


def run(book: Book, pages, on: bool) -> dict:
    stages = pipeline.run(book, pages, settings=replace(Settings.from_env(), quote_reader=on))
    paragraphs = [b for b in stages.doc.blocks if isinstance(b, Paragraph)]
    read = [
        s
        for s in stages.suspects
        if any(any(s.support.get(n, ())[1:]) for n in (quotes.READER, quotes.OPENED))
    ]
    return {
        "suspects": len(stages.suspects),
        "fixed": sum(s.choice == "other" for s in stages.suspects),
        "ocr questions": len(ocrdoubts.line_doubts(stages.suspects)),
        "quote lines": sorted((r.page, r.line) for r in stages.quote_lines),
        "unpaired in book": sum(len(quotes.problems(p.text)) for p in paragraphs),
        "quote suspects": [asdict(s) for s in read],
        "paragraphs": {
            f"{p.sources[0].page}.{p.sources[0].line}": p.text for p in paragraphs if p.sources
        },
    }


def main() -> None:
    for spec in sys.argv[1:]:
        name, _, span = spec.partition(":")
        pages = tuple(int(n) for n in span.split("-")) if span else None
        copy = OUT / name
        if not copy.exists():
            shutil.copytree(Path("work") / name, copy, ignore=shutil.ignore_patterns("epubs"))
        book = Book.load(copy)
        result = {}
        for label, on in (("off", False), ("on", True)):
            result[label] = r = run(book, pages, on)
            print(
                f"STEP {name} {label}: {r['suspects']} suspects, {r['fixed']} fixed, "
                f"{r['ocr questions']} OCR questions, {len(r['quote lines'])} quote lines, "
                f"{r['unpaired in book']} unpaired marks left, "
                f"{len(r['quote suspects'])} quote suspects",
                flush=True,
            )
        off, on = result["off"]["paragraphs"], result["on"]["paragraphs"]
        result["changed"] = [
            {"at": k, "off": off.get(k), "on": on.get(k)}
            for k in sorted(set(off) | set(on), key=lambda k: tuple(map(int, k.split("."))))
            if off.get(k) != on.get(k)
        ]
        by_choice: dict[str, int] = {}
        for s in result["on"]["quote suspects"]:
            by_choice[s["choice"]] = by_choice.get(s["choice"], 0) + 1
        print(f"STEP {name}: {len(result['changed'])} paragraphs changed; {by_choice}", flush=True)
        (OUT / f"{name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1))
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
