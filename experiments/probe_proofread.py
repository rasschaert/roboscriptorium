"""Can a local model proofread a human's review answers? The Stella proofreading test.

Items: every region a human answered in Stella's review, with the text exactly as
first answered (`regions.jsonl.before-proofread`), and the truth as proofread
against the scan (the answers file now). Seven items are wrong: five typing
slips, a speck kept as a period, and the text layer's "gedruktom". The rest are
right, so they measure false alarms.

Each item is asked two ways, each giving P(no) from the first token's
`top_logprobs` (no prose is parsed):
- vision: the crop and the text: does the text match the print exactly?
- text: the passage alone: is it free of typos and punctuation errors?

    uv run python experiments/probe_proofread.py MODEL [--limit N] [--read]

`--read` asks the model instead to transcribe each crop, and compares its reading
with the answer: where they differ, the reading either agrees with the truth (a
catch) or doesn't (a false alarm).

Results go to work/probes/proofread/stella/<model>.json.
"""

import base64
import io
import json
import math
import re
import sys
import time
from pathlib import Path

import httpx
import pymupdf
from PIL import Image
from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

from roboscriptorium.config import Settings
from roboscriptorium.corrections import Correction
from roboscriptorium.ocrcheck import line_boxes
from roboscriptorium.pdf import Line, PageText

BOOK = Path("work/stella")
OUT = Path("work/probes/proofread/stella")
PAD = 6
VISION = (
    "The image is cut from a scanned Dutch book. Below is a transcription of it.\n\n"
    "{text}\n\n"
    "Does the transcription match the printed text in the image exactly, letter for "
    "letter, including accents, quote marks (‘ ’ “ ”), commas and periods? Ignore line "
    "breaks and hyphenation at line ends. Answer with one word: yes or no."
)
TEXT = (
    "Below is a passage from a published Dutch novel, as transcribed from print.\n\n"
    "{text}\n\n"
    "Is the passage free of typos, misplaced or missing punctuation, and wrong quote "
    "marks, as a carefully edited book would print it? Answer with one word: yes or no."
)


def corrections(path: Path) -> dict[str, Correction]:
    out = {}
    for line in path.read_text().splitlines():
        raw = json.loads(line)
        for k in ("box", "span"):
            if raw.get(k):
                raw[k] = tuple(raw[k])
        out[raw["key"]] = Correction(**raw)
    return out


def items() -> list[dict]:
    before = corrections(BOOK / "review/regions.jsonl.before-proofread")
    now = corrections(BOOK / "review/regions.jsonl")
    found = []
    for key, c in before.items():
        if c.action != "text":
            continue
        answered = c.text if c.text is not None else c.original
        right = now[key].text if now[key].text is not None else now[key].original
        found.append(
            {"key": key, "page": c.page, "first": c.first, "last": c.last, "box": c.box,
             "text": answered, "truth": right, "wrong": answered != right}
        )  # fmt: skip
    # The layer's own misreading on p. 51, which the OCR check fixed without asking.
    found.append(
        {"key": "p51-gedruktom", "page": 51, "line_text": "gedruktom", "text": None,
         "truth": None, "wrong": True}
    )  # fmt: skip
    return found


def crop(pdf, layer, item) -> bytes:
    lines = layer[item["page"]]
    if item.get("line_text"):
        k = next(i for i, ln in enumerate(lines) if item["line_text"] in ln["text"])
        item["first"] = item["last"] = k
        item["text"] = lines[k]["text"]
        item["truth"] = lines[k]["text"].replace("gedruktom", "gedrukt om")
    # Each line's box as printed (its words' boxes), so no neighbouring line shows.
    page = PageText(item["page"], 0, 0, [Line(ln["text"], ln["x0"], ln["y0"], ln["x1"], ln["y1"]) for ln in lines])
    boxes = line_boxes(pdf[item["page"] - 1], page)[item["first"] : item["last"] + 1]
    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    clip = pymupdf.Rect(x0 - PAD, y0 - 2, x1 + PAD, y1 + 2)
    png = pdf[item["page"] - 1].get_pixmap(dpi=300, clip=clip).tobytes("png")
    # Under a megapixel, as vision models expect.
    image = Image.open(io.BytesIO(png))
    if image.width * image.height > 1_000_000:
        scale = (1_000_000 / (image.width * image.height)) ** 0.5
        image = image.resize((int(image.width * scale), int(image.height * scale)))
    buf = io.BytesIO()
    image.save(buf, "PNG")
    return buf.getvalue()


def p_no(model: str, prompt: str, png: bytes | None, url: str) -> tuple[float, float]:
    """P(no) against P(yes) from the first answer token, and the seconds taken."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "logprobs": True,
        "top_logprobs": 10,
        "options": {"num_predict": 1, "temperature": 0},
    }
    if png is not None:
        payload["images"] = [base64.b64encode(png).decode()]
    started = time.time()
    r = httpx.post(f"{url}/api/generate", json=payload, timeout=900)
    r.raise_for_status()
    top = r.json()["logprobs"][0]["top_logprobs"]
    p = {"yes": 0.0, "no": 0.0}
    for t in top:
        word = t["token"].strip().lower()
        if word in p:
            p[word] += math.exp(t["logprob"])
    total = p["yes"] + p["no"]
    return (p["no"] / total if total else math.nan), time.time() - started


READ = (
    "Transcribe the printed Dutch text in this image exactly as printed: every letter, "
    "accent, quote mark (‘ ’ “ ”) and punctuation mark. Keep the line breaks. Output only "
    "the text."
)
_FOLD = str.maketrans({"–": "-", "—": "-", "\u202f": " ", "\u2009": " ", "\u00a0": " "})


def fold(text: str) -> str:
    """Compared without line breaks, end-of-line hyphenation or dash and space kinds."""
    text = text.translate(_FOLD)
    text = re.sub(r"-\s*\n\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


def read(model: str, png: bytes, url: str) -> str:
    payload = {
        "model": model,
        "prompt": READ,
        "images": [base64.b64encode(png).decode()],
        "stream": False,
        "think": False,
        "options": {"num_predict": 400, "temperature": 0},
    }
    r = httpx.post(f"{url}/api/generate", json=payload, timeout=900)
    r.raise_for_status()
    return r.json()["response"].strip()


def main_read(model: str, limit: int | None) -> None:
    url = Settings.from_env().ollama_url
    layer = {
        p["number"]: p["lines"]
        for p in json.loads((BOOK / "stages/textlayer.json").read_text())["pages"]
    }
    found = items()[:limit] if limit else items()
    results, caught, alarms = [], 0, 0
    with pymupdf.open(BOOK / "source.pdf") as pdf:
        for item in found:
            png = crop(pdf, layer, item)
            reading = read(model, png, url)
            a, t = fold(item["text"]), fold(item["truth"])
            # The part of the reading that lines up with the answer.
            m = fuzz.partial_ratio_alignment(a, fold(reading))
            g = fold(reading)[m.dest_start : m.dest_end] if m else fold(reading)
            differs = g != a
            closer = Levenshtein.distance(g, t) < Levenshtein.distance(g, a)
            if item["wrong"] and differs and closer:
                caught += 1
            if not item["wrong"] and differs:
                alarms += 1
            results.append({**item, "box": None, "reading": reading})
            mark = "WRONG" if item["wrong"] else "right"
            note = "caught" if item["wrong"] and differs and closer else (
                "alarm" if differs and not item["wrong"] else "")
            print(f"p{item['page']:<3} {mark} {note:6} answer {a[:70]!r}\n{'':17}reading {g[:70]!r}",
                  flush=True)  # fmt: skip
    name = model.replace(":", "_").replace("/", "_")
    if not limit:
        (OUT / f"{name}-read.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
    wrong = sum(i["wrong"] for i in found)
    print(f"caught {caught}/{wrong} wrong answers; false alarms on {alarms}/{len(found) - wrong} right ones")


def main(model: str, limit: int | None) -> None:
    url = Settings.from_env().ollama_url
    layer = {
        p["number"]: p["lines"]
        for p in json.loads((BOOK / "stages/textlayer.json").read_text())["pages"]
    }
    found = items()[:limit] if limit else items()
    results = []
    with pymupdf.open(BOOK / "source.pdf") as pdf:
        for item in found:
            png = crop(pdf, layer, item)
            vision, t1 = p_no(model, VISION.format(text=item["text"]), png, url)
            text, t2 = p_no(model, TEXT.format(text=item["text"]), None, url)
            results.append({**item, "box": None, "vision_no": vision, "text_no": text})
            mark = "WRONG" if item["wrong"] else "right"
            print(f"p{item['page']:<3} {mark}  vision P(no) {vision:.2f} ({t1:.1f}s)  "
                  f"text P(no) {text:.2f} ({t2:.1f}s)  {item['text'][:60]!r}", flush=True)  # fmt: skip
    name = model.replace(":", "_").replace("/", "_")
    if not limit:
        (OUT / f"{name}.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
    for mode in ("vision_no", "text_no"):
        wrong = sorted((r[mode] for r in results if r["wrong"]), reverse=True)
        right = sorted((r[mode] for r in results if not r["wrong"]), reverse=True)
        if not wrong or not right:
            continue
        # How many right answers rank above the least suspicious wrong one, and the AUC.
        pairs = sum((w > r) + 0.5 * (w == r) for w in wrong for r in right)
        print(f"{mode}: wrong {[round(w, 2) for w in wrong]}; right ones above 0.5: "
              f"{sum(r > 0.5 for r in right)}/{len(right)}; AUC {pairs / (len(wrong) * len(right)):.2f}")  # fmt: skip


if __name__ == "__main__":
    args = sys.argv[1:]
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else None
    (main_read if "--read" in args else main)(args[0], limit)
