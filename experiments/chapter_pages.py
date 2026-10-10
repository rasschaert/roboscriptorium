"""The scan page each reference chapter starts on, to cut a bench slice at a chapter's end.

    uv run python experiments/chapter_pages.py <golden name> <scan id> [epub]

Reads the derived reference (`golden/<name>/text`, or `work/golden/<name>/text`) and the
scan's text layer, and finds each chapter's first words on the pages. No models.
"""

import re
import sys
from pathlib import Path

from roboscriptorium import pdf
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters, unmarked


def words(text: str) -> list[str]:
    return re.findall(r"[^\W_]+", unmarked(text).lower())


golden = Golden.load(sys.argv[1])
scan = next(s for s in golden.scans if s.id == sys.argv[2])
chapters = load_chapters(golden.data_root / "text")
pages = pdf.read_text_layer(Path(f"work/{golden.name}--{scan.id}/source.pdf"))
page_words = [(p.number, " ".join(words(" ".join(ln.text for ln in p.lines)))) for p in pages]
first = scan.body_pages[0]
for i, chapter in enumerate(chapters, 1):
    # Words 2–7: a drawn initial can cost the layer the first.
    probe = " ".join(words(" ".join(chapter.paragraphs))[1:7])
    found = next((n for n, w in page_words if n >= first and probe and probe in w), None)
    if found:
        first = found
    print(f"{i:3d}  p{found or '?':<5} {chapter.heading[:40]!r}  {probe!r}")
