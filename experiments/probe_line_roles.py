"""Probe a decision model on line roles: body vs anything else.

Usage: uv run python experiments/probe_line_roles.py MODEL [PER_CLASS]
Samples PER_CLASS (default 30) body and non-body lines from the Tauchnitz scan,
labelled by experiments/label_lines.py. Note that short body lines ("it.") are
often mislabelled "other" there, so read the listed misses before trusting the totals.
"""

import json, random, statistics, sys, time
from roboscriptorium.clients import ollaya

model = sys.argv[1]
PER_CLASS = int(sys.argv[2]) if len(sys.argv) > 2 else 30
d = "work/sense-and-sensibility--tauchnitz-1864/stages/"
labels = json.load(open(d + "line-labels.json"))
pages = json.load(open(d + "textlayer.json"))["pages"]
random.seed(7)
body = [k for k, v in labels.items() if v == "body"]
other = [k for k, v in labels.items() if v == "other"]
sample = [(k, "body") for k in random.sample(body, PER_CLASS)] + [(k, "other") for k in random.sample(other, PER_CLASS)]

def state(key):
    pg, i = map(int, key.split(":"))
    p = pages[pg - 1]; lines = p["lines"]; ln = lines[i]
    full = statistics.median(l["x1"] - l["x0"] for l in lines) or 1
    left = statistics.median(l["x0"] for l in lines)
    mid = (ln["x0"] + ln["x1"]) / 2
    return {
        "line": ln["text"],
        "line_number": f"{i + 1} of {len(lines)}",
        "vertical_position": f"{ln['y0'] / p['height']:.0%} down the page",
        "alignment": "centred" if abs(mid - p["width"] / 2) < 0.08 * p["width"] and (ln["x1"] - ln["x0"]) < 0.8 * full else ("indented" if ln["x0"] - left > 5 else "flush left"),
        "width": f"{(ln['x1'] - ln['x0']) / full:.0%} of a full line",
        "previous_line": lines[i - 1]["text"] if i else None,
        "next_line": lines[i + 1]["text"] if i + 1 < len(lines) else None,
    }

Q = {"role": ollaya.choice(
    "This is one line of text extracted from a scanned page of a printed book. What is it?",
    {"body": "Part of the running text of the book: prose or dialogue, including the short last line of a paragraph",
     "running_head": "The book or chapter title repeated at the top of every page, often with a page number",
     "page_number": "A page number on its own",
     "chapter_heading": "A chapter or part heading such as 'CHAPTER XII.'",
     "artifact": "Not part of the book's text: a library or digitisation stamp, a printer's signature mark at the bottom of a page, or scanning noise"})}
client = ollaya.for_model(model, "http://127.0.0.1:11435", "http://127.0.0.1:11434")
rows = []; t0 = time.time()
for key, gold in sample:
    a = client.decide(state(key), Q)["role"]
    rows.append((key, gold, a.value, a.probabilities.get("body", 0)))
dt = time.time() - t0
correct = sum((pred == "body") == (gold == "body") for _, gold, pred, _ in rows)
print(f"{model}: {correct}/{len(rows)} body-vs-other correct, {dt / len(rows) * 1000:.0f} ms/line")
for thr in (0.3, 0.5, 0.7, 0.9):
    tp = sum(g == "body" and pb >= thr for _, g, _, pb in rows); fp = sum(g == "other" and pb >= thr for _, g, _, pb in rows)
    fn = sum(g == "body" and pb < thr for _, g, _, pb in rows)
    print(f"  P(body)>={thr}: body kept {tp}/{PER_CLASS}, junk let through {fp}/{PER_CLASS}, body lost {fn}")
from collections import Counter
print("  predicted roles for 'other':", Counter(p for _, g, p, _ in rows if g == "other"))
print("  predicted roles for 'body':", Counter(p for _, g, p, _ in rows if g == "body"))
json.dump(rows, open(f"{d}probe-{model.replace(':', '_')}.json", "w"))
