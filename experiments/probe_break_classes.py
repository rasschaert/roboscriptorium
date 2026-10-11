"""Whether a reference EPUB's paragraph class marks scene breaks: crops of the scan around
a few paragraphs of the class, for a human (or agent) to look for the white space.

    uv run python experiments/probe_break_classes.py <golden> <class> opening|closing [n]

`opening`: the class sits on the paragraph after a break, so the crop shows the lines
above it; `closing`: on the paragraph before one, so the crop shows the lines below.
Paragraphs that open a chapter are skipped. Crops go to work/probes/break-classes/.
"""

import html
import re
import sys
import zipfile
from pathlib import Path

import pymupdf

from roboscriptorium import bench
from roboscriptorium.golden.manifest import Golden

name, cls, mode = sys.argv[1:4]
n = int(sys.argv[4]) if len(sys.argv) > 4 else 3
manifest = Golden.load(name)
ref = manifest.reference
spec = next(s for s in bench.SETS["tuning"] + bench.SETS["validation"] if s.startswith(name + "--"))
scan = Path("work") / spec.split(":")[0] / "source.pdf"
out = Path("work/probes/break-classes")
out.mkdir(parents=True, exist_ok=True)

paragraphs = []  # (class, text) in reading order, headings as None
with zipfile.ZipFile(Path("work/.cache/publisher") / f"{name}.epub") as z:
    members = z.namelist()
    for f in ref.files:
        x = z.read(next(m for m in members if m.endswith(f))).decode()
        for c, body in re.findall(r'<p class="([^"]*)"[^>]*>(.*?)</p>', x, re.S):
            text = " ".join(html.unescape(re.sub(r"<[^>]+>", "", body)).split())
            heading = any(c.startswith(h) for h in ref.heading_prefixes)
            paragraphs.append((None if heading else c, text))

picks = []
for i, (c, text) in enumerate(paragraphs):
    if c is None or cls not in c.split() or i == 0 or paragraphs[i - 1][0] is None:
        continue
    target = paragraphs[i + 1][1] if mode == "closing" and i + 1 < len(paragraphs) else text
    if len(target.split()) >= 5:
        picks.append(target)
step = max(1, len(picks) // n)
picks = picks[::step][:n]
print(f"{name} {cls}: {sum(1 for c, _ in paragraphs if c and cls in c.split())} paragraphs")
with pymupdf.open(scan) as pdf:
    for k, target in enumerate(picks):
        words = " ".join(target.split()[:4])
        for page in pdf:
            hits = page.search_for(words)
            if hits:
                r = hits[0]
                clip = pymupdf.Rect(0, r.y0 - 60, page.rect.width, r.y1 + 12)
                path = out / f"{name}-{cls}-{k}.png"
                page.get_pixmap(dpi=100, clip=clip).save(path)
                print(f"  p{page.number + 1}: {words!r} → {path}")
                break
        else:
            print(f"  not found on the scan: {words!r}")
