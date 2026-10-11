"""The questions a review would still ask of a book: each unanswered one with its crop.

Builds the book from its caches, finds the flags as `roboscriptorium review` does, and
writes sheets of the unanswered questions' crops plus a text listing to
work/probes/questions/<book>/, for sampling them before a reviewer is sent.

    uv run python experiments/sample_questions.py work/stella
"""

import json
import sys
from collections import Counter
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw
from proofread_answers import PER_SHEET, WIDTH, crop

from roboscriptorium import flags, layout, ocrcheck, pipeline
from roboscriptorium.book import Book
from roboscriptorium.corrections import Corrections


def main(book_dir: str) -> None:
    book = Book.load(Path(book_dir))
    st = pipeline.run(book)
    regions = layout.detect(book.source, [p.number for p in st.pages], book.stages / "layout.json")
    found = flags.find(
        st.pages,
        st.model_roles,
        regions,
        ocrcheck.doubts(st.suspects),
        st.quote_lines,
        st.quote_readings,
        st.faint_pages,
    )
    answers = Corrections(book.corrections_path)
    open_ = [f for f in found if answers.for_flag(f) is None]
    out = Path("work/probes/questions") / Path(book_dir).name
    out.mkdir(parents=True, exist_ok=True)
    pages = {p.number: p for p in st.pages}
    listing = []
    with pymupdf.open(book.source) as pdf:
        for start in range(0, len(open_), PER_SHEET):
            batch = open_[start : start + PER_SHEET]
            crops = [crop(pdf, pages[f.page], f) for f in batch]
            sheet = Image.new("RGB", (WIDTH, sum(c.height + 40 for c in crops)), "white")
            draw, y = ImageDraw.Draw(sheet), 0
            for n, (f, c) in enumerate(zip(batch, crops, strict=True), start + 1):
                draw.text((8, y + 8), f"#{n}  p{f.page}  {', '.join(f.reasons)}", fill=(200, 0, 0))
                sheet.paste(c, (0, y + 36))
                y += c.height + 40
                listing.append(
                    {
                        "n": n,
                        "page": f.page,
                        "treatment": f.treatment,
                        "reasons": f.reasons,
                        "text": f.text,
                        "readings": [r["text"] for r in f.readings],
                        "votes": [r["votes"] for r in f.readings],
                    }
                )
            sheet.save(out / f"sheet-{start // PER_SHEET + 1:02}.png")
    (out / "questions.json").write_text(json.dumps(listing, ensure_ascii=False, indent=1))
    kinds = Counter(r for q in listing for r in q["reasons"])
    print(f"{len(found)} questions, {len(open_)} unanswered: {out}")
    for reason, n in kinds.most_common():
        print(f"  {n:4} {reason}")


if __name__ == "__main__":
    main(sys.argv[1])
