"""Probe: does imajev tell which quarter turn makes a plate upright?

Each page is rendered at the four turns (clockwise, as `probe_orientation.py` turns
them) and asked whether the picture is upright; the turn it is surest of is its answer.

    uv run python experiments/probe_upright.py <port> work/the-story-of-doctor-dolittle--stokes-1920 \\
        6:90 25:90 57:90 83:90 87:90 90:90 107:90 198:0 200:90 36:0
"""

import io
import sys
from pathlib import Path

import pymupdf

from roboscriptorium.clients import decide, llama

Q = {"upright": decide.choice(
    "Is this page of a printed book shown the right way up, so its picture stands upright "
    "and any caption or text under it reads left to right?",
    {"yes": "The page is upright", "no": "The page is turned sideways or upside down"},
)}  # fmt: skip

port, book = sys.argv[1], Path(sys.argv[2])
client = llama.ReadoutClient("imajev-4b", f"http://127.0.0.1:{port}")
right = 0
with pymupdf.open(book / "source.pdf") as doc:
    for arg in sys.argv[3:]:
        n, _, truth = arg.partition(":")
        page = doc[int(n) - 1]
        zoom = (900_000 / (page.rect.width * page.rect.height)) ** 0.5
        image = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).pil_image()
        p = {}
        for turn in (0, 90, 180, 270):
            buf = io.BytesIO()
            image.rotate(-turn, expand=True).save(buf, "PNG")
            a = client.decide("A scanned page from a printed book.", Q, image_png=buf.getvalue())
            p[turn] = a["upright"].probabilities["yes"]
        best = max(p, key=p.get)
        right += best == int(truth)
        print(f"p{n}: truth {truth}, picked {best}  " + "  ".join(f"{t}:{v:.2f}" for t, v in p.items()))
print(f"{right}/{len(sys.argv) - 3} right")
