"""How many pages a book does the bench need? A saved bench run, rescored on each book's
first N slice pages: the pooled wrong words a page after review and its 95% bootstrap
interval, as `bench.pooled` weighs books (each the same, pages resampled within a book).

Only books whose slice holds at least the largest N take part, so every N scores the
same books.

    uv run python experiments/probe_bench_pages.py [bench.json] [N ...]

No models; seconds.
"""

import json
import random
import sys
from pathlib import Path

from roboscriptorium import bench

AFTER_REVIEW = 3  # bench.page_counts: wrong words after review at the mean slip rate

args = sys.argv[1:]
path = Path(args.pop(0)) if args and args[0].endswith(".json") else max(
    bench.OUT.glob("tuning-*.json"), key=lambda p: p.stat().st_mtime
)
sizes = [int(a) for a in args] or [10, 20, 45, 90]
record = json.loads(path.read_text())
pages = {
    name: [v[AFTER_REVIEW] for _, v in sorted(b["pages"].items(), key=lambda kv: int(kv[0]))]
    for name, b in record["books"].items()
}
full = {n: p for n, p in pages.items() if len(p) >= max(sizes)}
print(f"{path.name}: {len(full)} of {len(pages)} books hold {max(sizes)} pages or more: "
      + ", ".join(n.split("--")[0] for n in full))


def interval(books: list[list[float]], level: float = 0.95) -> tuple[float, float, float]:
    rng = random.Random(0)
    mean = sum(sum(b) / len(b) for b in books) / len(books)
    means = sorted(
        sum(sum(rng.choices(b, k=len(b))) / len(b) for b in books) / len(books)
        for _ in range(bench.BOOTSTRAP_SAMPLES)
    )
    tail = (1 - level) / 2
    n = bench.BOOTSTRAP_SAMPLES
    return mean, means[int(tail * n)], means[int((1 - tail) * n) - 1]


for size in sizes:
    mean, low, high = interval([p[:size] for p in full.values()])
    print(f"first {size:3} pages: {mean:.2f} wrong words a page after review, "
          f"95% {low:.2f}–{high:.2f} (width {high - low:.2f})")
mean, low, high = interval(list(pages.values()))
print(f"every book, its whole slice: {mean:.2f}, 95% {low:.2f}–{high:.2f} (width {high - low:.2f})")
