"""Visual lines that change when grouping ignores large initials: old cache against a fresh read.

Reads `stages/textlayer.json` (the cached, previous grouping) and the PDF again.
"""

import json
import sys
from pathlib import Path

from roboscriptorium.pdf import read_text_layer

for book in sys.argv[1:]:
    cached = json.loads((Path(book) / "stages" / "textlayer.json").read_text())["pages"]
    fresh = read_text_layer(Path(book) / "source.pdf")
    changed = []
    for old, new in zip(cached, fresh, strict=True):
        a = [ln["text"] for ln in old["lines"]]
        b = [ln.text for ln in new.lines]
        if a != b:
            changed.append((new.number, sorted(set(a) - set(b)), sorted(set(b) - set(a))))
    print(f"{Path(book).name}: {len(changed)} pages changed", flush=True)
    for number, gone, came in changed[:3]:
        print(f"  p{number}")
        for t in gone:
            print(f"    - {t[:100]}")
        for t in came:
            print(f"    + {t[:100]}")
