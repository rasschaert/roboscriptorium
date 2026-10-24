"""Where would a candidate witness tell the arbiter something new? On the frozen reader set,
per candidate reading file: lines where the text layer, qwen and glm-ocr agree on a wrong
reading (quiet: the OCR check raises no suspect there, so only a new witness can) and the
candidate is right there; lines it is right on alone; and quiet right lines it contradicts
(a new suspect the arbiter must reject). No models.

    uv run python experiments/witness_score.py <reading file stem> [more …]
"""

import json
import sys
from collections import Counter
from pathlib import Path

from roboscriptorium.trustdata import fold

SET = Path("work/tryout/reader-v3")


def readings(stem: str) -> dict[str, str]:
    return json.loads((SET / "readings" / f"{stem}.json").read_text())


if __name__ == "__main__":
    items = json.loads((SET / "items.json").read_text())["items"]
    qwen, glm = readings("qwen3.8_27b-nvfp4"), readings("glm-ocr_bf16")
    for stem in sys.argv[1:]:
        cand = readings(stem)
        c = Counter()
        for i in items:
            t = fold(i["truth"])
            k, q, g, layer = (fold(x) for x in (cand[i["id"]], qwen[i["id"]], glm[i["id"]], i["layer"]))
            quiet = q == g == layer
            c["quiet wrong"] += quiet and q != t
            c["right on quiet wrong"] += quiet and q != t and k == t
            c["quiet right"] += quiet and q == t
            c["contradicts quiet right"] += quiet and q == t and k != t
            c["right alone"] += k == t and q != t and g != t
            c["wrong where qwen right"] += q == t and k != t
        print(f"{stem:28} {dict(c)}")
