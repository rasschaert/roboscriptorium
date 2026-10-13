"""Build the OCR check's trust data on golden books (`roboscriptorium.trustdata`).

    uv run python experiments/ocr_trust_data.py [--rebuild] [book …]
"""

import sys

from roboscriptorium.trustdata import SPECS, load

if __name__ == "__main__":
    names = [a for a in sys.argv[1:] if not a.startswith("--")] or list(SPECS)
    for name in names:
        rows = load(name, "--rebuild" in sys.argv)
        settled = [r for r in rows if r["settled"]]
        wrong = sum(not r["right"][0] for r in settled)  # the text layer's version
        print(f"{name[:34]:34} {len(rows):4} suspects, {len(settled):4} settled, "
              f"layer wrong on {wrong}", flush=True)  # fmt: skip
