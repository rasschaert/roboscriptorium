"""Scores a line detector's P(the transcription is exact) on the frozen reader set: how well
it separates the hard lines (the text layer is wrong) from the control lines (it is right),
and how many hard lines it would flag at a given share of control lines flagged.

    uv run python experiments/triage_score.py <label>

Reads work/tryout/reader-v2/triage/<label>.json (`h2o_triage.py`). No models.
"""

import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[2] if len(sys.argv) > 2 else "work/tryout/reader-v2")


def auc(low: list[float], high: list[float]) -> float:
    """P(a random hard line scores below a random control line), ties half."""
    wins = sum((a < b) + 0.5 * (a == b) for a in low for b in high)
    return wins / (len(low) * len(high))


if __name__ == "__main__":
    score = json.loads((ROOT / "triage" / f"{sys.argv[1]}.json").read_text())
    items = [i for i in json.loads((ROOT / "items.json").read_text())["items"] if i["id"] in score]
    hard = [score[i["id"]] for i in items if i["stratum"] == "hard"]
    control = sorted(score[i["id"]] for i in items if i["stratum"] == "control")
    print(f"{len(hard)} hard, {len(control)} control lines; AUC {auc(hard, control):.3f}")
    for share in (0.02, 0.05, 0.10, 0.20):
        cut = control[int(share * len(control))]
        flagged = sum(h < cut for h in hard)
        print(f"flag below {cut:.3f}: {share:4.0%} of control, {flagged}/{len(hard)} hard "
              f"({flagged / len(hard):.0%})")
