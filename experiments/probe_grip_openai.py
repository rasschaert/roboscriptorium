"""Ways of asking a reader on a local OpenAI-compatible server (Unsloth Studio), tried on a
slice of the quiet set (`quiet_set.py`): its lines every reader gets wrong and a seeded
sample of those they get right. A grip is a `+`-joined list of:

    think   thinking on (`reasoning_effort` medium, 4096 tokens); the answer's first line
    x2      the crop scaled up twice (Lanczos)

    uv run python experiments/probe_grip_openai.py <model id> <grip> [right sample, 40]

Readings go to work/probes/grip/<model stem>/<grip>.json with seconds and thinking length
per line; each run prints the lines it reads right where all are wrong, and the right lines
it contradicts. The plain grip's readings are the quiet set's own.
"""

import base64
import io
import json
import random
import sys
import time
from pathlib import Path

import httpx
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from quiet_set import ROOT  # noqa: E402
from tryout import OPENAI_LOCAL_URL, SEED, fold, sha  # noqa: E402

from roboscriptorium import readers  # noqa: E402


def png_of(item: dict, grip: set[str]) -> bytes:
    raw = (ROOT / "crops" / f"{sha(item['id'])}.png").read_bytes()
    if "x2" not in grip:
        return raw
    im = Image.open(io.BytesIO(raw))
    im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, "PNG")
    return out.getvalue()


def ask(model: str, png: bytes, prompt: str, grip: set[str]) -> tuple[str, int]:
    think = "think" in grip
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64," + base64.b64encode(png).decode()
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "temperature": 0,
        "max_tokens": 4096 if think else readers.MAX_LINE_TOKENS,
        "chat_template_kwargs": {"enable_thinking": think},
        "reasoning_effort": "medium" if think else "none",
    }
    resp = httpx.post(OPENAI_LOCAL_URL, json=body, timeout=1800)
    resp.raise_for_status()
    msg = resp.json()["choices"][0]["message"]
    text = (msg.get("content") or "").strip()
    if "</think>" in text:
        text = text.split("</think>")[-1].strip()
    return text.split("\n")[0].strip(), len(msg.get("reasoning_content") or "")


def main() -> None:
    model, grip_name = sys.argv[1], sys.argv[2]
    n_right = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    grip = set(grip_name.split("+"))
    items = json.loads((ROOT / "items.json").read_text())["items"]
    right = [i for i in items if i["stratum"] == "right"]
    chosen = [i for i in items if i["stratum"] == "wrong"]
    chosen += random.Random(SEED).sample(right, n_right)
    prompts = {
        b: json.loads((Path("work") / b / "stages" / "third-reading.json").read_text())["prompt"]
        for b in {i["book"] for i in chosen}
    }
    stem = model.replace(":", "_").replace("/", "_")
    out = Path("work/probes/grip") / stem / f"{grip_name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = json.loads(out.read_text()) if out.exists() else {}
    for n, i in enumerate([i for i in chosen if i["id"] not in done], 1):
        start = time.time()
        text, thought = ask(model, png_of(i, grip), prompts[i["book"]], grip)
        done[i["id"]] = {"text": text, "seconds": round(time.time() - start, 1), "thought": thought}
        out.write_text(json.dumps(done, ensure_ascii=False, indent=1))
        mark = "=" if fold(text) == fold(i["truth"]) else "≠"
        print(
            f"{n}/{len(chosen)} {i['stratum']:5} {mark} {done[i['id']]['seconds']:>6}s {text!r}",
            flush=True,
        )
    wrong_right = [
        i
        for i in chosen
        if i["stratum"] == "wrong" and fold(done[i["id"]]["text"]) == fold(i["truth"])
    ]
    contradicts = [
        i
        for i in chosen
        if i["stratum"] == "right" and fold(done[i["id"]]["text"]) != fold(i["truth"])
    ]
    secs = sum(d["seconds"] for d in done.values()) / len(done)
    print(
        f"\n{grip_name}: right where all wrong {len(wrong_right)}/23, contradicts right {len(contradicts)}/{n_right}, {secs:.1f} s a line"
    )
    for i in contradicts:
        print(f"  contradicts: {done[i['id']]['text']!r} | {i['truth']!r}")


if __name__ == "__main__":
    main()
