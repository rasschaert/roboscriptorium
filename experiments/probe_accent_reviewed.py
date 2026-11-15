"""The accent measure against a reviewed book of the user's (no golden pair needed): the
built book after their answers is the label. Each plain word of the text layer is paired
with the word the built book has in its place (the block's lines aligned word by word);
where that carries an acute the layer lacks, the measure had a mark to find. Prints what
it finds at the fixed cut and at cuts set from the book's own plain words, and the marked
forms the print uses that the measure never drew. Reads `stages/accent-marks.json`
(`probe_accent_doubts.py <book> --stages`). No models.

    uv run python experiments/probe_accent_reviewed.py <book dir name>
"""

import json
import re
import sys
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

from roboscriptorium import accentmarks

WORD = re.compile(r"[^\W\d_]+")
ACUTE = set("áéíóúÁÉÍÓÚ")


def strip(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if not unicodedata.combining(c))


def main():
    stages = Path("work") / sys.argv[1] / "stages"
    doc = json.loads((stages / "document.json").read_text())
    layer = {p["number"]: p["lines"] for p in json.loads((stages / "textlayer.json").read_text())["pages"]}
    fits = json.loads((stages / "accent-marks.json").read_text())["fits"]
    found, plain, undrawn, shapes = [], [], Counter(), Counter()
    for block in (b for b in doc["blocks"] if "text" in b):
        scan = [
            (s["page"], s["line"], m.start(), m.group())
            for s in block.get("sources", [])
            if s["page"] in layer and s["line"] < len(layer[s["page"]])
            for m in WORD.finditer(layer[s["page"]][s["line"]]["text"])
        ]
        built = WORD.findall(block["text"])
        match = SequenceMatcher(None, [strip(w[3]).lower() for w in scan], [strip(w).lower() for w in built], autojunk=False)
        for a, b, n in match.get_matching_blocks():
            for i in range(n):
                page, line, at, word = scan[a + i]
                ours = built[b + i]
                fit = fits.get(f"{page}|{line}|{at}|{word}")
                if not fit or strip(word) != word:
                    continue
                if ours == word:
                    plain.append(fit[0])
                elif ACUTE & set(ours) and strip(ours) == word:
                    if ours in accentmarks.stressed(word):
                        found.append(fit[0] if fit[1] == ours else 0.0)
                    else:
                        undrawn[ours] += 1
                        group = re.search(r"[aeiouáéíóú]+", ours[ours.index(next(c for c in ours if c in ACUTE)) - 0 :], re.I)
                        shapes[strip(group.group()).lower() + " as " + group.group().lower()] += 1
    found, plain = np.array(found), np.array(plain)
    print(f"{len(plain)} plain words; {len(found)} accents the layer lacks in a form the measure draws; {sum(undrawn.values())} in a form it doesn't")
    print(f"  fixed cut {accentmarks.CUT}: finds {int((found >= accentmarks.CUT).sum())} of {len(found)}, offers {int((plain >= accentmarks.CUT).sum())} plain words")
    for share in (0.999, 0.9975, 0.995, 0.99):
        cut = float(np.quantile(plain, share))
        print(f"  cut at the book's {share:.2%} of plain words ({cut:.2f}): finds {int((found >= cut).sum())}, offers {int((plain >= cut).sum())} plain words")
    print("  forms not drawn:", shapes.most_common(12))
    print("  e.g.", undrawn.most_common(15))


if __name__ == "__main__":
    main()
