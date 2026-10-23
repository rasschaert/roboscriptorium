"""Fine-tune Laya (multilingual) as a line-role decision model on MLX, from the certain rows
of `laya_roles_data.py`, and predict the validation books' rows for `laya_roles_eval.py`.
Runs in Unsloth Studio's Python (it brings MLX and FastDecisionModel):

    ~/.unsloth/studio/unsloth_studio/bin/python -I experiments/laya_roles_train.py \
        <label> [max_steps] [body_lines]

Trains on the tuning books and the training-only slices, never a validation book; every
heading and other row, and `body_lines` body rows (default 10000) drawn at random, 5% of
them held out to calibrate. Writes work/probes/laya-roles/predictions-<label>.jsonl and the
merged model (~0.7 GB, the only save MLX offers) to ~/models/roboscriptorium/laya-roles/<label>/:
weights stay out of the backed-up project folder.
"""

import json
import random
import sys
import time
from pathlib import Path

from transformers import TrainingArguments
from unsloth import DecisionTrainer, FastDecisionModel

ROOT = Path("work/probes/laya-roles")
MODELS = Path.home() / "models/roboscriptorium/laya-roles"
BASE = "convaiinnovations/laya-multilingual"
# bench.SETS["validation"], by book folder: never trained on.
VALIDATION = {
    "de-kerk-van-de-dode-meisjes--ia-scan", "vuurspel--ia-scan",
    "youre-never-weird-on-the-internet--ia-scan", "de-stilte-van-de-hel--ia-scan",
    "het-laatste-bevel--ia-scan", "the-strangers-child--ia-scan", "normal-people--ia-scan",
    "verminkt--ia-scan", "de-geruchten--ia-scan", "vanille-en-andere-smaken--dbnl-scan",
}  # fmt: skip

label = sys.argv[1]
max_steps = int(sys.argv[2]) if len(sys.argv) > 2 else -1
body_lines = int(sys.argv[3]) if len(sys.argv) > 3 else 10000


def read(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines()]


train, held = [], []
for path in sorted(ROOT.glob("*.jsonl")):
    if path.stem.startswith("predictions"):
        continue
    (held if path.stem in VALIDATION else train).extend(read(path))
rng = random.Random(0)
body = [r for r in train if r["gold"]["role"] == "body"]
rest = [r for r in train if r["gold"]["role"] != "body"]
chosen = rest + rng.sample(body, min(body_lines, len(body)))
rng.shuffle(chosen)
print(f"training rows {len(chosen)} (body {min(body_lines, len(body))} of {len(body)}, "
      f"other and heading {len(rest)}); validation rows {len(held)}", flush=True)

model, tokenizer = FastDecisionModel.from_pretrained(BASE)
model = FastDecisionModel.get_peft_model(model, r=16, lora_alpha=16)
fields = [{"state": r["state"], "questions": r["questions"], "gold": r["gold"]} for r in chosen]
items, report = FastDecisionModel.build_dataset(fields, tokenizer, model)
print("dataset:", report, flush=True)
train_items, eval_items = FastDecisionModel.split_holdout(items, seed=3407)
args = TrainingArguments(
    output_dir="/tmp/laya-roles-checkpoints", per_device_train_batch_size=8,
    gradient_accumulation_steps=2, num_train_epochs=2, max_steps=max_steps,
    learning_rate=2e-4, lr_scheduler_type="cosine", logging_steps=10, save_strategy="no",
    report_to="none", seed=3407,
)  # fmt: skip
start = time.time()
DecisionTrainer(model=model, args=args, train_dataset=train_items, eval_dataset=eval_items,
                processing_class=tokenizer).train()  # fmt: skip
print(f"trained in {(time.time() - start) / 60:.1f} min", flush=True)
print("calibration:", FastDecisionModel.calibrate(model, tokenizer, eval_items), flush=True)
model.save_pretrained_merged(str(MODELS / label), tokenizer)
FastDecisionModel.for_inference(model)
start = time.time()
with (ROOT / f"predictions-{label}.jsonl").open("w") as f:
    for n, r in enumerate(held, 1):
        a = FastDecisionModel.predict(model, tokenizer, r["state"], r["questions"])["role"]
        f.write(json.dumps({"book": r["book"], "page": r["page"], "line": r["line"],
                            "role": a["answer"], "p": a["probabilities"]}) + "\n")  # fmt: skip
        if n % 2000 == 0:
            print(f"predicted {n}/{len(held)}", flush=True)
print(f"predicted {len(held)} rows in {(time.time() - start) / 60:.1f} min", flush=True)
