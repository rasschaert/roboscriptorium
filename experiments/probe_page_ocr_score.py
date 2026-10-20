"""Scores whole-page readings against the tuning bench's errors on those pages: does the
reading hold what the reference has (`want`) rather than what our build has (`got`)?

    uv run python experiments/probe_page_ocr_score.py <label> [glm|qwen …]

`<label>` names a folder of Markdown readings (`mlx_read_pages.py`); glm and qwen add the
build's own page readings (`pagereader.py` caches) for the same pages. Words are compared
as a run, so a word split across a line end counts as joined.
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from roboscriptorium.evaluate import normalise

ROOT = Path("work/probes/olmocr-pages")


def words(text: str) -> str:
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    return " " + normalise(re.sub(r"[#*_]", "", text)).lower() + " "


def verdict(reading: str, row: dict) -> str:
    want, got = words(row["want"]).strip(), words(row["got"]).strip()
    has_want = bool(want) and f" {want} " in reading
    has_got = bool(got) and f" {got} " in reading
    if want and has_want and not has_got:
        return "agrees with the reference"
    if not want and got and not has_got:
        return "agrees with the reference"
    if has_got and not has_want:
        return "agrees with our build"
    return "neither"


def cached(book: str, page: int, kind: str) -> str:
    path = Path("work") / book / "stages" / f"page-reading-{kind}-page.json"
    if not path.exists():
        return ""
    return json.loads(path.read_text())["pages"].get(str(page), "")


if __name__ == "__main__":
    label, others = sys.argv[1], sys.argv[2:]
    manifest = json.loads((ROOT / "pages.json").read_text())
    tally: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for name, rows in manifest.items():
        book, page = name.rsplit("_", 1)
        file = ROOT / label / f"{name}.md"
        if not file.exists():
            continue
        readings = {label: file.read_text()} | {k: cached(book, int(page), k) for k in others}
        if not all(readings.values()):
            continue  # compared only where every reading exists
        for who, text in readings.items():
            for row in rows:
                tally[(who, row["cause"])][verdict(words(text), row)] += 1
    for (who, cause), t in sorted(tally.items()):
        n = sum(t.values())
        print(f"{who:10} {cause:22} {n:3}  reference {t['agrees with the reference']:3}  "
              f"build {t['agrees with our build']:3}  neither {t['neither']:3}")
