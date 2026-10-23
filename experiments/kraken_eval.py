"""Does a character recogniser with no language model fail differently from the readers?
(the deep-research reports' first idea, 2026-10-23). Two Kraken models, each trained on the
line crops of half the frozen reader set's books (and the tuning books outside the set),
each scored on the other half's frozen lines.

    uv run python experiments/kraken_eval.py lists     # training lists per fold (no models)
    ~/models/roboscriptorium/kraken-env/bin/ketos -d mps --workers 4 train -f path -u NFD \\
        -B 16 -q early --min-epochs 5 -o ~/models/roboscriptorium/kraken/<fold> \\
        -t work/probes/kraken/<fold>.txt
    ~/models/roboscriptorium/kraken-env/bin/python -I experiments/kraken_eval.py read <fold> <model>
    uv run python experiments/kraken_eval.py score

`read` runs in Kraken's own environment and writes work/probes/kraken/readings-<fold>.json
({item id: reading}). `score` counts, on the hard lines, where Kraken reads the truth while
the text layer, qwen and glm-ocr all agree on the same wrong reading (the silent kind), and
its errors on the control lines.
"""

import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path("work/probes/kraken")
LINES = Path.home() / "models/roboscriptorium/kraken/lines"
SET = Path("work/tryout/reader-v3")


def folds() -> dict[str, list[str]]:
    books = sorted(json.loads((SET / "items.json").read_text())["books"])
    return {"a": books[0::2], "b": books[1::2]}


def lists() -> None:
    f = folds()
    held = {b for bs in f.values() for b in bs}
    for name, test in f.items():
        train = [
            str(png)
            for d in sorted(LINES.iterdir())
            if d.name not in test
            for png in sorted(d.glob("*.png"))
        ]
        (ROOT / f"{name}.txt").write_text("\n".join(train) + "\n")
        print(f"fold {name}: test books {test}; training lines {len(train)}"
              f" (books outside the set: {sorted(d.name for d in LINES.iterdir() if d.name not in held)})")


def read(fold: str, model_path: str) -> None:
    from kraken import rpred
    from kraken.containers import BBoxLine, Segmentation
    from kraken.lib import models
    from PIL import Image

    hashes = __import__("hashlib")
    net = models.load_any(model_path)
    test = set(folds()[fold])
    items = [i for i in json.loads((SET / "items.json").read_text())["items"] if i["book"] in test]
    out = {}
    for n, item in enumerate(items, 1):
        name = hashes.sha256(item["id"].encode()).hexdigest()[:16]
        im = Image.open(SET / "crops" / f"{name}.png")
        seg = Segmentation(
            type="bbox", imagename="", text_direction="horizontal-lr", script_detection=False,
            lines=[BBoxLine(id="l", bbox=(0, 0, im.width, im.height))],
        )  # fmt: skip
        text = "".join(r.prediction for r in rpred.rpred(net, im, seg))
        out[item["id"]] = unicodedata.normalize("NFC", text)
        if n % 100 == 0:
            print(f"{n}/{len(items)}", flush=True)
    (ROOT / f"readings-{fold}.json").write_text(json.dumps(out, ensure_ascii=False))


def score() -> None:
    from roboscriptorium.trustdata import fold as same

    items = json.loads((SET / "items.json").read_text())["items"]
    qwen = json.loads((SET / "readings" / "qwen3.8_27b-nvfp4.json").read_text())
    glm = json.loads((SET / "readings" / "glm-ocr_bf16.json").read_text())
    kraken = {}
    for f in ("a", "b"):
        path = ROOT / f"readings-{f}.json"
        if path.exists():
            kraken.update(json.loads(path.read_text()))
    c = {}
    for i in items:
        if i["id"] not in kraken:
            continue
        t = same(i["truth"])
        k, q, g, layer = (same(x) for x in (kraken[i["id"]], qwen[i["id"]], glm[i["id"]], i["layer"]))
        s = c.setdefault(i["stratum"], {"lines": 0, "kraken right": 0, "qwen right": 0})
        s["lines"] += 1
        s["kraken right"] += k == t
        s["qwen right"] += q == t
        silent = q == g == layer != t
        s["silent (layer, qwen, glm agree, wrong)"] = s.get("silent (layer, qwen, glm agree, wrong)", 0) + silent
        s["kraken right where silent"] = s.get("kraken right where silent", 0) + (silent and k == t)
        s["kraken right alone"] = s.get("kraken right alone", 0) + (k == t and q != t and g != t)
        s["kraken breaks where qwen right"] = s.get("kraken breaks where qwen right", 0) + (q == t and k != t)
    for stratum, s in c.items():
        print(stratum, s)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "lists":
        lists()
    elif cmd == "read":
        read(sys.argv[2], sys.argv[3])
    else:
        score()
