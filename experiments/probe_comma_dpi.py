"""Does a line's last comma read right at a higher resolution?

Places where the OCR check turned a text layer's line-end comma into a full stop (all
three readers' crops are at `readers.DPI`): each line is cropped as the readers see it
and again at more dpi, and glm-ocr reads each. Prints, per dpi, how often the reading
ends in the layer's comma and how often in a stop.

    uv run python experiments/probe_comma_dpi.py [dpi …]

Needs Ollama (glm-ocr). The crop is `readers._line_crop` with its resolution changed.
"""

import json
import sys
from pathlib import Path

import pymupdf

from roboscriptorium import readers
from roboscriptorium.config import Settings

BOOKS = ["de-vergelding--ia-scan", "de-kerk-van-de-dode-meisjes--ia-scan"]
DPIS = [int(a) for a in sys.argv[1:]] or [300, 450, 600]


def places() -> list[tuple[str, int, int, str]]:
    out = []
    for book in BOOKS:
        stages = Path("work") / book / "stages"
        layer = next(p for n in ("textlayer.json", "text-layer.json") if (p := stages / n).exists())
        pages = json.loads(layer.read_text())["pages"]
        for s in json.loads((stages / "ocr-check.json").read_text()):
            end = s["ours"][-1:]
            if s["choice"] == "other" and s["chosen"] and end == "," and s["chosen"][-1:] == ".":
                page = next(p for p in pages if p["number"] == s["page"])
                out.append((book, s["page"], s["line"], page["lines"][s["line"]]["text"]))
    return out


def main() -> None:
    settings = Settings.from_env()
    found = places()
    print(f"{len(found)} places where a line-end comma became a stop")
    tally = {d: {",": 0, ".": 0, "other": 0} for d in DPIS}
    for book, number, line, text in found:
        doc = pymupdf.open(Path("work") / book / "source.pdf")
        page = json.loads(
            next(
                p
                for n in ("textlayer.json", "text-layer.json")
                if (p := Path("work") / book / "stages" / n).exists()
            ).read_text()
        )["pages"]
        ln = next(p for p in page if p["number"] == number)["lines"][line]
        box = (ln["x0"], ln["y0"], ln["x1"], ln["y1"])
        row = []
        for dpi in DPIS:
            em = box[3] - box[1]
            clip = pymupdf.Rect(
                box[0] - em, box[1] - readers.LINE_PAD, box[2] + em, box[3] + readers.LINE_PAD
            )
            png = doc[number - 1].get_pixmap(dpi=dpi, clip=clip).tobytes("png")
            read = readers.read_line(png, settings.ocr_model, settings.ollama_url).strip()
            end = read[-1:] if read[-1:] in ",." else "other"
            tally[dpi][end] += 1
            row.append(f"{dpi}:{read[-12:]!r}")
        print(f"{book[:12]} p{number} l{line}  layer {text[-10:]!r}  " + "  ".join(row), flush=True)
    for dpi, t in tally.items():
        print(f"{dpi} dpi: ends in comma {t[',']}, stop {t['.']}, other {t['other']}")


main()
