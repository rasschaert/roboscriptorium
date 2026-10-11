"""Contact sheets of a book's first and last pages, for labelling page kinds by eye.

Each sheet shows up to 16 pages, small, each with its PDF page number and how many
words its text layer holds: the edges, where the text proper starts and ends, and any
page inside with fewer than `SHORT` words (a part title, a blank, a motto). Sheets go to work/probes/page-kinds/<book>/.

    uv run python experiments/page_sheets.py <book dir> [first N] [last N]
"""

import sys
from pathlib import Path

import pymupdf

book = Path(sys.argv[1])
head = int(sys.argv[2]) if len(sys.argv) > 2 else 16
tail = int(sys.argv[3]) if len(sys.argv) > 3 else 12
WIDTH, COLS, PER_SHEET = 190, 8, 16
SHORT = 60

out = Path("work/probes/page-kinds") / book.name
out.mkdir(parents=True, exist_ok=True)
with pymupdf.open(book / "source.pdf") as doc:
    n = doc.page_count
    short = {p for p in range(1, n + 1) if len(doc[p - 1].get_text().split()) < SHORT}
    pages = sorted({*range(1, min(head, n) + 1), *range(max(1, n - tail + 1), n + 1), *short})
    for s in range(0, len(pages), PER_SHEET):
        group = pages[s : s + PER_SHEET]
        thumbs = []
        for p in group:
            page = doc[p - 1]
            pix = page.get_pixmap(matrix=pymupdf.Matrix(WIDTH / page.rect.width, WIDTH / page.rect.width))
            thumbs.append((p, len(page.get_text().split()), pix))
        cell_h = max(t[2].height for t in thumbs) + 18
        rows = (len(thumbs) + COLS - 1) // COLS
        sheet = pymupdf.open()
        canvas = sheet.new_page(width=COLS * (WIDTH + 6), height=rows * cell_h)
        for k, (p, words, pix) in enumerate(thumbs):
            x, y = (k % COLS) * (WIDTH + 6), (k // COLS) * cell_h
            canvas.insert_image(pymupdf.Rect(x, y + 16, x + pix.width, y + 16 + pix.height), pixmap=pix)
            canvas.insert_text((x + 2, y + 12), f"p{p}  {words}w", fontsize=11, color=(0.8, 0, 0))
        name = out / f"sheet-{group[0]:03d}-{group[-1]:03d}.png"
        canvas.get_pixmap(dpi=72).save(name)
        print(name)
