"""LightOnOCR-3 as a reader of the frozen reader set (docs/checklist.md, "New OCR models as
witnesses"). Runs in its own environment, as LightOnOCR needs a newer transformers than the
project's; writes the readings where `tryout.py` and `vote_sim.py` look for them.

    ~/models/roboscriptorium/lighton-env/bin/python -I experiments/lighton_read.py \\
        ~/models/roboscriptorium/lightonocr-3-1b [n] [--scale 2] [--pad 120] [--set quiet]
    uv run python experiments/tryout.py run reader lighton-3-1b   # scores, reads nothing
    uv run python experiments/vote_sim.py lighton-3-1b

The model is asked as its card says for transcription: the image alone, no prompt, thinking
off, but greedy rather than sampled, as every reader on the set is. Its first non-empty line
is the reading. `n` reads the first n lines, prints them beside the truth and writes nothing;
`--scale` enlarges each crop before the processor sees it, `--pad` sets it on a white margin
of that many pixels (a bare line crop sends the model into endless repetition on some scans),
`--set quiet` reads the quiet set (`quiet_set.py`) instead.
"""

import hashlib
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import torch
from PIL import Image, ImageOps

SETS = {"reader": Path("work/tryout/reader-v3"), "quiet": Path("work/tryout/quiet-v1")}
MAX_TOKENS = 200


def load(model_dir: Path):
    config = json.loads((model_dir / "config.json").read_text())
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    if config["model_type"] == "mistral3":
        from transformers import LightOnOcrForConditionalGeneration, LightOnOcrProcessor

        from safetensors.torch import load_file

        # The card runs this architecture in float32 on MPS. The checkpoint nests the text
        # model's weights one level deeper than this class names them; the head is tied.
        model = LightOnOcrForConditionalGeneration.from_pretrained(model_dir, dtype=torch.float32)
        weights = {
            re.sub(r"^language_model\.model\.", "model.language_model.", k): v
            for k, v in load_file(model_dir / "model.safetensors").items()
        }
        missing, unexpected = model.load_state_dict(weights, strict=False)
        model.tie_weights()
        assert not unexpected and set(missing) <= {"lm_head.weight"}, (missing, unexpected)
        processor = LightOnOcrProcessor.from_pretrained(model_dir)
    else:
        from transformers import AutoProcessor, Qwen3_5ForConditionalGeneration

        model = Qwen3_5ForConditionalGeneration.from_pretrained(model_dir, dtype=torch.bfloat16)
        processor = AutoProcessor.from_pretrained(model_dir)
    return model.to(device).eval(), processor, device


def read(model, processor, device: str, image: Image.Image) -> str:
    conversation = [{"role": "user", "content": [{"type": "image", "image": image}]}]
    inputs = processor.apply_chat_template(
        conversation, add_generation_prompt=True, tokenize=True, return_dict=True,
        return_tensors="pt", enable_thinking=False,
    )  # fmt: skip
    dtype = model.dtype
    inputs = {
        k: v.to(device=device, dtype=dtype) if v.is_floating_point() else v.to(device)
        for k, v in inputs.items()
    }
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=MAX_TOKENS, do_sample=False)
    text = processor.decode(out[0, inputs["input_ids"].shape[1] :], skip_special_tokens=True)
    lines = [s.strip() for s in text.split("\n") if s.strip()]
    return unicodedata.normalize("NFC", lines[0] if lines else "")


if __name__ == "__main__":
    args = sys.argv[1:]
    opts = {"--scale": 1.0, "--pad": 0.0, "--set": "reader"}
    for flag in opts:
        if flag in args:
            k = args.index(flag)
            opts[flag] = args[k + 1] if flag == "--set" else float(args[k + 1])
            del args[k : k + 2]
    scale, pad, SET = opts["--scale"], int(opts["--pad"]), SETS[opts["--set"]]
    model_dir = Path(args[0]).expanduser()
    limit = int(args[1]) if len(args) > 1 else None
    name = model_dir.name.replace("lightonocr-", "lighton-") + (f"+x{scale:g}" if scale != 1 else "") + (f"+pad{pad}" if pad else "")
    out_path = SET / "readings" / f"{name}.json"
    done = json.loads(out_path.read_text()) if out_path.exists() and not limit else {}
    model, processor, device = load(model_dir)
    items = json.loads((SET / "items.json").read_text())["items"]
    todo = [i for i in items if i["id"] not in done][:limit]
    start = time.time()
    for n, item in enumerate(todo, 1):
        crop = hashlib.sha256(item["id"].encode()).hexdigest()[:16]
        im = Image.open(SET / "crops" / f"{crop}.png").convert("RGB")
        if scale != 1:
            im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        if pad:
            im = ImageOps.expand(im, pad, fill="white")
        done[item["id"]] = read(model, processor, device, im)
        if limit:
            mark = "=" if done[item["id"]] == item["truth"] else "≠"
            print(f"{mark} {done[item['id']]!r}\n  {item['truth']!r}", flush=True)
        elif n % 25 == 0 or n == len(todo):
            out_path.write_text(json.dumps(done, ensure_ascii=False))
            print(f"{n}/{len(todo)}", flush=True)
    if todo:
        print(f"{(time.time() - start) / len(todo):.2f} s a line on {device}", flush=True)
