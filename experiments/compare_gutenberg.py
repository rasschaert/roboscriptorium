"""Compare a Project Gutenberg EPUB with a golden book's derived reference text.

Usage: uv run python experiments/compare_gutenberg.py <golden name> <gutenberg.epub>

Prints how many words differ and the most frequent differences (reference → PG),
so we can see which Standard Ebooks changes survive the derivation.
"""

import difflib
import re
import sys
import zipfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

from roboscriptorium.evaluate import normalise
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters


class Paragraphs(HTMLParser):
    """Text of each <p>, skipping PG boilerplate, transcriber's notes and captions."""

    SKIP_CLASSES = ("pg-boilerplate", "transnote", "caption", "illus", "figcenter", "toc")

    def __init__(self):
        super().__init__()
        self.paragraphs, self._buf, self._in_p, self._skip = [], [], False, 0

    def handle_starttag(self, tag, attrs):
        cls = (dict(attrs).get("class") or "") + " " + (dict(attrs).get("id") or "")
        if self._skip or any(s in cls for s in self.SKIP_CLASSES):
            self._skip += 1
        if tag == "p":
            self._in_p, self._buf = True, []

    def handle_endtag(self, tag):
        if tag == "p" and self._in_p:
            self._in_p = False
            if not self._skip and (text := " ".join("".join(self._buf).split())):
                self.paragraphs.append(text)
        if self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._in_p:
            self._buf.append(data)


def gutenberg_words(epub: Path) -> list[str]:
    with zipfile.ZipFile(epub) as z:
        names = sorted(
            (n for n in z.namelist() if re.search(r"-h-\d+\.htm\.html$", n)),
            key=lambda n: int(re.search(r"-h-(\d+)\.htm", n).group(1)),
        )
        parser = Paragraphs()
        for n in names:
            parser.feed(z.read(n).decode())
    return normalise(" ".join(parser.paragraphs)).split()


def reference_words(name: str) -> list[str]:
    chapters = load_chapters(Golden.load(name).text_dir)
    return normalise(" ".join(p for c in chapters for p in c.paragraphs)).split()


ref = reference_words(sys.argv[1])
pg = gutenberg_words(Path(sys.argv[2]))
diffs: Counter = Counter()
changed = 0
for op, a0, a1, b0, b1 in difflib.SequenceMatcher(None, ref, pg, autojunk=False).get_opcodes():
    if op != "equal":
        changed += max(a1 - a0, b1 - b0)
        diffs[(" ".join(ref[a0:a1])[:60], " ".join(pg[b0:b1])[:60])] += 1
print(f"reference {len(ref)} words, gutenberg {len(pg)} words, ~{changed} differ")
for (a, b), n in diffs.most_common(int(sys.argv[3]) if len(sys.argv) > 3 else 40):
    print(f"  {n:4}× {a!r} → {b!r}")
