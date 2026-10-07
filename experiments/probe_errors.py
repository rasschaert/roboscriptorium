"""Every remaining difference of a golden book, with its kind and whether a question covers it.

    uv run python experiments/probe_errors.py work/goede-dochter--ia-scan:9-64:1-4 …

Prints one line per difference: page, kind, asked/unasked, output → reference, and
the OCR check's suspect on that line if there is one.
"""

import sys
from pathlib import Path

from roboscriptorium import disagreements, flags, layout, ocrcheck, pipeline, quality
from roboscriptorium.book import Book
from roboscriptorium.cli import _range, _verdicts
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters


def main(specs: list[str]) -> None:
    for spec in specs:
        book_dir, pages, chapters = (spec.split(":") + [None, None])[:3]
        book = Book.load(Path(book_dir))
        stages = pipeline.run(book, pages=_range(pages or None))
        regions = None
        if layout.available():
            numbers = [p.number for p in stages.pages]
            regions = layout.detect(book.source, numbers, book.stages / "layout.json")
        found = flags.find(
            stages.pages,
            stages.model_roles,
            regions,
            ocrcheck.doubts(stages.suspects),
            stages.quote_lines,
        )
        reference = load_chapters(Golden.load(book.golden).text_dir)
        if (span := _range(chapters or None)) is not None:
            reference = reference[span[0] - 1 : span[1]]
        reference, _ = disagreements.patch(reference, _verdicts(book))
        errors = disagreements.find(stages.doc, reference, stages.corrected)
        suspects = {}
        for s in stages.suspects:
            suspects.setdefault((s.page, s.line), []).append(s)
        print(f"== {Path(book_dir).name}: {len(errors)} differences")
        for e in sorted(errors, key=lambda e: (e.page or 0, e.lines or (0, 0))):
            asked = any(quality.catches(f, e) for f in found)
            notes = []
            if e.lines:
                for k in range(e.lines[0], e.lines[1] + 1):
                    for s in suspects.get((e.page, k), []):
                        notes.append(f"[{s.choice} {s.ours!r}→{s.chosen or s.others} {s.votes}]")
            print(
                f"p{e.page} {quality.category(e):13} {'asked' if asked else 'UNASKED':7} "
                f"{e.got!r} → {e.want!r}   …{e.before[-30:]}|{e.after[:30]}… {' '.join(notes)}"
            )


if __name__ == "__main__":
    main(sys.argv[1:])
