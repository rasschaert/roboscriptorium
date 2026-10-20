"""Which reader keeps an emphasis accent? The 12 audited stress-accent lines (the unasked set's
crops) read by glm-ocr on Ollama and, through `mlx_read_crops.py`'s setup, by olmOCR: does the
reading hold the reference's word (`want`) or the build's (`got`)?

    uv run python experiments/probe_accent_readers.py glm
    work/models/mlx-env/bin/python -I experiments/probe_accent_readers.py olmocr <model dir>

Prints one row per line and a total. Needs `unasked_set.py`'s crops.
"""

import hashlib
import json
import sys
from pathlib import Path

RUN = "tuning-20261020T182636-f38e636-dirty"
ROOT = Path("work/probes/unasked-set")


def lines() -> list[tuple[str, str, str, bytes]]:
    items = {i["id"] for i in json.loads((ROOT / "items.json").read_text())["items"]}
    out = []
    for x in Path(f"work/bench/{RUN}.errors.jsonl").read_text().splitlines():
        r = json.loads(x)
        if r["cause"] != "stress accent" or r["asked"] or r["layer"] != "kept" or not r["lines"]:
            continue
        iid = f'{r["book"]}:{r["page"]}:{r["lines"][0]}'
        if r["lines"][0] == r["lines"][1] and iid in items:
            png = (ROOT / "crops" / f"{hashlib.sha256(iid.encode()).hexdigest()[:16]}.png").read_bytes()
            out.append((r["want"].strip("‘’'\".,;:!?"), r["got"].strip("‘’'\".,;:!?"), iid, png))
    return out


def report(name: str, read) -> None:
    held = [0, 0]
    for want, got, iid, png in lines():
        reading = read(iid, png)
        held[0] += want in reading
        held[1] += got in reading
        print(f"{iid[:34]:34} want {want!r:12} got {got!r:12} reading holds: want {int(want in reading)} got {int(got in reading)}")
    print(name, "holds the reference's word / the build's word:", held)


if __name__ == "__main__":
    if sys.argv[1] == "glm":
        from roboscriptorium import readers
        from roboscriptorium.config import Settings

        s = Settings.from_env()
        report("glm-ocr", lambda iid, png: readers.read_line(png, s.ocr_model, s.ollama_url))
    else:
        import tempfile

        from mlx_vlm import generate, load
        from mlx_vlm.prompt_utils import apply_chat_template
        from mlx_vlm.utils import load_config

        model, processor = load(sys.argv[2])
        config = load_config(sys.argv[2])
        text = apply_chat_template(
            processor, config, "Transcribe the text in this image exactly as printed. Return only the text, on one line.", num_images=1
        )

        def read(iid, png):
            with tempfile.NamedTemporaryFile(suffix=".png") as f:
                f.write(png)
                f.flush()
                res = generate(model, processor, text, image=[f.name], max_tokens=200, temperature=0.0, verbose=False)
            return str(getattr(res, "text", res)).strip().split("\n")[0]

        report(sys.argv[1], read)
