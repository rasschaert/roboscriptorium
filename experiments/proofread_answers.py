"""A second look at a book's review answers: every question's crop, readings and answer.

Writes numbered sheets of crops (six to an image) and a text listing to
work/probes/proofread/<book>/, for checking a human's answers against the scan.

    uv run python experiments/proofread_answers.py work/stella
"""

import io
import json
import sys
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw

from roboscriptorium import flags, layout, ocrcheck, pipeline
from roboscriptorium.book import Book
from roboscriptorium.corrections import Corrections

PER_SHEET = 6
PAD = 6  # points around the crop
WIDTH = 1400  # pixels per crop on a sheet


def crop(pdf: pymupdf.Document, page, f: flags.Flag) -> Image.Image:
    if f.box is not None:
        x0, y0, x1, y1 = f.box
    else:
        lines = page.lines[f.first : f.last + 1]
        x0, y0 = min(ln.x0 for ln in lines), min(ln.y0 for ln in lines)
        x1, y1 = max(ln.x1 for ln in lines), max(ln.y1 for ln in lines)
    # A place in a line is shown with the whole line around it, for context.
    if f.span is not None:
        line = page.lines[f.first]
        x0, x1 = min(x0, line.x0), max(x1, line.x1)
    clip = pymupdf.Rect(x0 - PAD, y0 - PAD, x1 + PAD, y1 + PAD)
    pix = pdf[f.page - 1].get_pixmap(dpi=400, clip=clip)
    image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
    if f.box is not None and f.span is not None:
        draw = ImageDraw.Draw(image)
        scale = 400 / 72
        bx0, by0, bx1, by1 = f.box
        draw.rectangle(
            [(bx0 - clip.x0) * scale - 2, (by0 - clip.y0) * scale - 2,
             (bx1 - clip.x0) * scale + 2, (by1 - clip.y0) * scale + 2],
            outline=(220, 0, 0), width=3,
        )  # fmt: skip
    ratio = WIDTH / image.width
    return image.resize((WIDTH, max(1, int(image.height * ratio))))


def main(book_dir: str) -> None:
    book = Book.load(Path(book_dir))
    st = pipeline.run(book)
    regions = layout.detect(book.source, [p.number for p in st.pages], book.stages / "layout.json")
    found = flags.find(
        st.pages, st.model_roles, regions, ocrcheck.doubts(st.suspects), st.quote_lines
    )
    answers = Corrections(book.corrections_path)
    out = Path("work/probes/proofread") / Path(book_dir).name
    out.mkdir(parents=True, exist_ok=True)
    pages = {p.number: p for p in st.pages}
    listing = []
    with pymupdf.open(book.source) as pdf:
        for start in range(0, len(found), PER_SHEET):
            batch = found[start : start + PER_SHEET]
            crops = [crop(pdf, pages[f.page], f) for f in batch]
            sheet = Image.new("RGB", (WIDTH, sum(c.height + 40 for c in crops)), "white")
            draw, y = ImageDraw.Draw(sheet), 0
            for n, (f, c) in enumerate(zip(batch, crops, strict=True), start + 1):
                draw.text((8, y + 8), f"#{n}  p{f.page}  {', '.join(f.reasons)}", fill=(200, 0, 0))
                sheet.paste(c, (0, y + 36))
                y += c.height + 40
                answer = answers.for_flag(f)
                listing.append(
                    {
                        "n": n,
                        "page": f.page,
                        "reasons": f.reasons,
                        "text": f.text,
                        "readings": [r["text"] for r in f.readings],
                        "votes": [r["votes"] for r in f.readings],
                        "answer": None
                        if answer is None
                        else {"action": answer.action, "text": answer.text, "span": answer.span},
                    }
                )
            sheet.save(out / f"sheet-{start // PER_SHEET + 1:02}.png")
    (out / "questions.json").write_text(json.dumps(listing, ensure_ascii=False, indent=1))
    print(f"{len(found)} questions, {sum(q['answer'] is not None for q in listing)} answered: {out}")


if __name__ == "__main__":
    main(sys.argv[1])
