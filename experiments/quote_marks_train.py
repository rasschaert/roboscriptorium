"""Trees that read the quote marks at a word's edge off the scan (`quote_marks_data.py`),
each book called by trees trained on the others. Against the text layer's marks at the
same edges: how often each is right, what the trees would offer where they differ from
the layer (right, wrong), and the nested marks (a single and a double together) found.
No models.

    uv run python experiments/quote_marks_train.py [--sure 0.9]
"""

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

DATA = Path("work/probes/quote-marks")
sure = float(sys.argv[sys.argv.index("--sure") + 1]) if "--sure" in sys.argv else 0.9


def features(r: dict) -> list[float]:
    return [float(r["opening"]), r["runs"], *r["widths"], *r["gaps"], r["span"], r["ink"], r["high"], *r["picture"]]


books = {p.stem: json.loads(p.read_text()) for p in sorted(DATA.glob("*.json"))}
counts = Counter(r["truth"] for rows in books.values() for r in rows)
classes = [c for c, n in counts.items() if n >= 20]
print("labels:", counts.most_common(12))


def label(r: dict) -> str:
    return r["truth"] if r["truth"] in classes else "other"


total = Counter()
nested_rows = []
for name, rows in books.items():
    train = [r for other, rs in books.items() if other != name for r in rs]
    model = HistGradientBoostingClassifier(max_depth=6, max_iter=200, learning_rate=0.1, random_state=0)
    model.fit(np.array([features(r) for r in train], np.float32), [label(r) for r in train])
    probs = model.predict_proba(np.array([features(r) for r in rows], np.float32))
    c = Counter()
    for r, p in zip(rows, probs, strict=True):
        said, conf = model.classes_[int(p.argmax())], float(p.max())
        truth, layer = label(r), r["layer"]
        marked = bool(truth or layer)
        c["edges with a mark"] += marked
        c["layer right"] += marked and layer == truth
        c["trees right"] += marked and said == truth
        if said != layer and conf >= sure:
            c["offers"] += 1
            c["offers right"] += said == truth
            c["offers where the layer was right"] += layer == truth
        if layer != truth:
            c["layer wrong"] += 1
            c["layer wrong, trees sure and right"] += said == truth and conf >= sure
        if truth in ("sd", "ds"):
            c["nested"] += 1
            c["nested the layer lacks"] += layer != truth
            c["nested the layer lacks, trees sure and right"] += layer != truth and said == truth and conf >= sure
            nested_rows.append((name[:10], r["page"], r["text"], layer, said, round(conf, 2)))
        elif said in ("sd", "ds") and conf >= sure:
            c["nested called where there is none"] += 1
    total.update(c)
    print(f"{name[:30]:30}", dict(c), flush=True)
print("all:", dict(total))
print("nested the trees miss:", [n for n in nested_rows if n[4] not in ("sd", "ds")][:30])
