"""Paragraph breaks the reference has and a build's EPUB lacks, with their context.

    uv run python experiments/probe_missed_breaks.py <golden-name> <build.epub> [chapters]

`chapters` (as "1-15") limits the reference to those chapters. Prints each missed
break as "…last words ¶ first words…" and counts how the paragraph before it ends.
"""

import difflib
import html
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path



def paragraphs(xhtml: str) -> list[str]:
    found = re.findall(r"<p\b[^>]*>(.*?)</p>", xhtml, flags=re.S)
    texts = [" ".join(html.unescape(re.sub(r"<[^>]+>", "", p)).split()) for p in found]
    return [t for t in texts if t]


def words_and_breaks(paras: list[str]) -> tuple[list[str], set[int]]:
    words, breaks = [], set()
    for p in paras:
        breaks.add(len(words))
        words += [re.sub(r"\W", "", w.lower()) or w for w in p.split()]
    return words, breaks


name, epub = sys.argv[1], sys.argv[2]
chapters = sorted(Path("work/golden", name, "text").glob("chapter-*.xhtml"), key=lambda p: int(p.stem.split("-")[1]))
if len(sys.argv) > 3:
    a, b = map(int, sys.argv[3].split("-"))
    chapters = [c for c in chapters if a <= int(c.stem.split("-")[1]) <= b]
ref = [p for c in chapters for p in paragraphs(c.read_text())]
with zipfile.ZipFile(epub) as z:
    out = [p for n in sorted(z.namelist()) if n.endswith(".xhtml") and "nav" not in n for p in paragraphs(z.read(n).decode())]

rw, rb = words_and_breaks(ref)
ow, ob = words_and_breaks(out)
sm = difflib.SequenceMatcher(None, rw, ow, autojunk=False)
to_out = {}
for i, j, n in sm.get_matching_blocks():
    for k in range(n):
        to_out[i + k] = j + k
missed, ends = [], Counter()
flat = [w for p in ref for w in p.split()]
for i in sorted(rb):
    if i == 0 or i not in to_out or to_out[i] in ob:
        continue
    before, after = " ".join(flat[max(0, i - 6):i]), " ".join(flat[i:i + 6])
    missed.append(f"…{before} ¶ {after}…")
    ends[flat[i - 1][-1]] += 1
print(f"reference breaks {len(rb)}, output breaks {len(ob)}, missed {len(missed)}")
print("previous paragraph ends with:", ends.most_common(8))
for m in missed[:40]:
    print(" ", m)
