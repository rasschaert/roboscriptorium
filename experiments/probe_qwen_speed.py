"""Probe: where Qwen's time per line goes, and how its throughput scales with concurrency.

`decompose`: a few line crops sent as the pipeline sends them, then text alone, image
alone, and with the instructions in the system turn ahead of the image, reading each
response's token counts and timings. Also how many prompts the runner keeps cached.

`scale`: disjoint sets of body lines read at 1, 2, 4, 8 and 16 requests at a time
(disjoint, so the runner's prompt cache can't flatter a later pass); then the first
set again at the widest setting and, with the instructions as the system turn, to count
readings that differ from the one-at-a-time pass. Results in work/probes/qwen-speed.json.

    uv run python experiments/probe_qwen_speed.py decompose|scale [lines per set] [--no-layout]
    ROBO_PROBE_MODEL=qwen3.8:27b-q8_0 uv run python experiments/probe_qwen_speed.py scale 64 --no-layout
"""

import base64
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pymupdf

from roboscriptorium import ocrcheck, quotes
from roboscriptorium.pdf import cached_text_layer

URL = "http://127.0.0.1:11434/api/generate"
# Another build of the reader: ROBO_PROBE_MODEL=qwen3.8:27b-q8_0
MODEL = os.environ.get("ROBO_PROBE_MODEL", "qwen3.8:27b-nvfp4")
BOOK = Path("work/goede-dochter--ia-scan")
PROMPT = quotes.style_prompt("nl", True, "...", "–")
OUT = Path("work/probes") / f"qwen-speed-{MODEL.replace(':', '_').replace('/', '_')}.json"


def crops_from(first_page: int, want: int) -> list[tuple[str, bytes]]:
    """(the layer's text, crop) for body lines of at least five words, from `first_page` on."""
    pages = cached_text_layer(BOOK / "source.pdf", BOOK / "stages" / "textlayer.json")
    out = []
    with pymupdf.open(BOOK / "source.pdf") as doc:
        for page in pages:
            if page.number < first_page:
                continue
            boxes = ocrcheck.line_boxes(doc[page.number - 1], page)
            for k, line in enumerate(page.lines):
                if len(line.text.split()) >= 5:
                    span = ocrcheck.crop_span(boxes, k)
                    out.append((line.text, ocrcheck._line_crop(doc, page.number, boxes[k], span)))
                if len(out) >= want:
                    return out
    return out


def call(png: bytes | None, prompt: str, system: str | None = None) -> dict:
    body = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {"num_predict": ocrcheck.MAX_LINE_TOKENS, "temperature": 0},
    }
    if png is not None:
        body["images"] = [base64.b64encode(png).decode()]
    if system is not None:
        body["system"] = system
    t = time.time()
    r = httpx.post(URL, json=body, timeout=600).json()
    r["wall"] = time.time() - t
    return r


def first_line(r: dict) -> str:
    return r.get("response", "").strip().split("\n")[0].strip()


def show(label: str, r: dict) -> None:
    if "error" in r:
        print(f"{label:34} ERROR {r['error']}")
        return
    print(
        f"{label:34} prompt {r.get('prompt_eval_count', 0):4} tok {r.get('prompt_eval_duration', 0) / 1e9:5.2f}s"
        f"  out {r.get('eval_count', 0):3} tok {r.get('eval_duration', 0) / 1e9:5.2f}s"
        f"  wall {r['wall']:5.2f}s  {first_line(r)!r}"
    )


def decompose() -> None:
    lines = crops_from(30, 8)
    a, b, c = (png for _, png in lines[:3])
    print("-- the pipeline's layout: instructions after the image, each a new line")
    show("A, as pipeline", call(a, PROMPT))
    show("B, as pipeline", call(b, PROMPT))
    show("A again (whole-prompt cache?)", call(a, PROMPT))
    print("-- the parts")
    show("text only, no image", call(None, PROMPT))
    show("A, image + 'Transcribe.'", call(a, "Transcribe."))
    show("A, same image, other text", call(a, PROMPT + " Output the line."))
    print("-- instructions as the system turn, ahead of the image")
    show("A, system layout", call(a, "Transcribe.", PROMPT))
    show("B, system layout (prefix reuse?)", call(b, "Transcribe.", PROMPT))
    show("C, system layout", call(c, "Transcribe.", PROMPT))
    print("-- how many prompts the runner keeps: A after 5 others")
    for _, png in lines[3:8]:
        call(png, PROMPT)
    show("A after 5 others", call(a, PROMPT))
    show("A after 5 others, system layout", call(a, "Transcribe.", PROMPT))


def read_set(crops: list[bytes], workers: int, system: bool) -> tuple[list[dict], float]:
    def one(png: bytes) -> dict:
        return call(png, "Transcribe.", PROMPT) if system else call(png, PROMPT)

    start = time.time()
    with ThreadPoolExecutor(workers) as pool:
        out = list(pool.map(one, crops))
    return out, time.time() - start


def scale(per_set: int, layout: bool = True) -> None:
    settings = (1, 2, 4, 8, 16)
    lines = crops_from(30, per_set * (len(settings) + 1))
    sets = [lines[i * per_set : (i + 1) * per_set] for i in range(len(settings) + 1)]
    assert all(len(s) == per_set for s in sets), f"only {len(lines)} lines"
    results = {}
    base = None
    for workers, crops in zip(settings, sets):
        rs, took = read_set([png for _, png in crops], workers, False)
        toks = sum(r.get("eval_count", 0) for r in rs)
        results[f"x{workers}"] = {"s_per_line": took / per_set, "out_tok_s": toks / took,
                                  "readings": [first_line(r) for r in rs],
                                  "layer": [t for t, _ in crops]}
        print(f"{workers:2} at a time: {took / per_set:5.2f} s a line, {toks / took:5.1f} output tok/s"
              f"  (a fresh set of {per_set})", flush=True)
        if workers == 1:
            base = results["x1"]["readings"]
    widest = settings[-1]
    if not layout:
        rs, _ = read_set([png for _, png in sets[0]], widest, False)
        wide = [first_line(r) for r in rs]
        differ = sum(a != b for a, b in zip(base, wide, strict=True))
        print(f"set 1 again, {widest} at a time: {differ} of {per_set} differ from 1 at a time")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.with_name(OUT.stem + "-parallel.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
        return
    # The system layout on a fresh set (its prefill is real), then the same set in the
    # pipeline's layout (its images now cached, so only its readings count).
    fresh = [png for _, png in sets[-1]]
    rs, took = read_set(fresh, widest, True)
    pe = sum(r.get("prompt_eval_count", 0) for r in rs) / per_set
    pd = sum(r.get("prompt_eval_duration", 0) for r in rs) / per_set / 1e9
    sys_readings = [first_line(r) for r in rs]
    print(f"system layout, fresh set, {widest} at a time: {took / per_set:5.2f} s a line, "
          f"{pe:.0f} prompt tok and {pd:.2f} s prefill a line", flush=True)
    rs, _ = read_set(fresh, widest, False)
    pipe_readings = [first_line(r) for r in rs]
    differ = sum(a != b for a, b in zip(sys_readings, pipe_readings, strict=True))
    results[f"fresh x{widest} system"] = {"s_per_line": took / per_set, "prompt_tok": pe,
                                          "prefill_s": pd, "differ": differ,
                                          "readings": sys_readings, "pipeline": pipe_readings}
    print(f"   {differ} of {per_set} system-layout readings differ from the pipeline's layout")
    for a, b in zip(pipe_readings, sys_readings):
        if a != b:
            print(f"   pipeline {a!r} -> system {b!r}")
    # The first set again at the widest setting: the readings against one at a time.
    rs, _ = read_set([png for _, png in sets[0]], widest, False)
    wide = [first_line(r) for r in rs]
    differ = sum(a != b for a, b in zip(base, wide, strict=True))
    results[f"set1 x{widest}"] = {"differ": differ, "readings": wide}
    print(f"set 1 again, {widest} at a time: {differ} of {per_set} readings differ from 1 at a time")
    for a, b in zip(base, wide):
        if a != b:
            print(f"   x1 {a!r} -> x{widest} {b!r}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "decompose":
        decompose()
    else:
        scale(int(sys.argv[2]) if len(sys.argv) > 2 else 64, "--no-layout" not in sys.argv)
