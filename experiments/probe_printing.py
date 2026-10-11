"""Probe: does a scan print the same text as its reference, or another printing? No models.

Aligns the scan's text layer with the derived reference word by word and lists where
they differ, sorted into what a reading slip makes (a word the word list lacks, one
letter off, punctuation) and what only an edited text makes: a known word for another
known word, or words added or left out. A pair whose reference was made from another
printing is fit when the second kind is no more than its OCR noise.

`--ij` reads y as ij on both sides, for an old OCR that wrote the Dutch ij as y.

    uv run python experiments/probe_printing.py <golden name> [--ij]
"""

import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pymupdf
from rapidfuzz.distance import Levenshtein

from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.lexicon import Lexicon

name = sys.argv[1]
ij = "--ij" in sys.argv
golden = Golden.load(name)
scan = golden.scans[0]
book = golden.book_dir(scan)
lex = Lexicon.load("nld" if golden.language == "nl" else "eng")


def words(text: str) -> list[str]:
    text = re.sub(r"[-¬\xad]\s*\n\s*(?=[a-zà-ÿ])", "", text)  # line-end hyphens
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    out = text.split()
    return [w.replace("ij", "y").replace("IJ", "Y") for w in out] if ij else out


with pymupdf.open(book / "source.pdf") as doc:
    first, last = scan.body_pages
    layer = words("\n".join(doc[p - 1].get_text() for p in range(first, last + 1)))
ref = words("\n".join(p for c in load_chapters(golden.text_dir) for p in c.paragraphs))


def bare(w: str) -> str:
    return re.sub(r"[^\wà-ÿ]", "", w)


def plain(w: str) -> str:
    """The word without its accents, lowercase: OCR drops and swaps accents."""
    return unicodedata.normalize("NFD", bare(w).lower()).encode("ascii", "ignore").decode()


def known(w: str) -> bool:
    b = bare(w)
    return bool(b) and (lex.knows(b) or lex.knows(b.replace("y", "ij")))


kinds: Counter = Counter()
edits: list[str] = []
for op in Levenshtein.opcodes(layer, ref):
    if op.tag == "equal":
        continue
    a, b = layer[op.src_start : op.src_end], ref[op.dest_start : op.dest_end]
    if op.tag == "replace" and len(a) == len(b):
        for x, y in zip(a, b, strict=True):
            if bare(x) == bare(y):
                kinds["punctuation"] += 1
            elif plain(x) == plain(y):
                kinds["accent"] += 1
            elif not known(x):
                kinds["unknown word (a slip)"] += 1
            elif Levenshtein.distance(bare(x).lower(), bare(y).lower()) <= 1 and len(bare(y)) <= 3:
                kinds["short word, a letter off"] += 1
            else:
                kinds["known word for another"] += 1
                edits.append(f"{x} → {y}")
        continue
    # Words only one side has: a page number or running head on the scan, or an edit.
    if all(re.fullmatch(r"\d+|[A-Z ]+", w) for w in a) and not b:
        kinds["page furniture"] += 1
        continue
    kinds[f"words {'only on the scan' if a and not b else 'only in the reference' if b and not a else 'rewritten'}"] += 1
    edits.append(f"{' '.join(a) or '∅'} → {' '.join(b) or '∅'}")

print(f"{name}: {len(layer)} words on the scan, {len(ref)} in the reference{' (y read as ij)' if ij else ''}")
for kind, n in kinds.most_common():
    print(f"  {n:6}  {kind}")
out = Path("work/probes/printing") / f"{name}.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(edits) + "\n")
print(f"edits that aren't slips: {len(edits)}, listed in {out}")
for e, n in Counter(edits).most_common(40):
    print(f"  {n:3}  {e}")
