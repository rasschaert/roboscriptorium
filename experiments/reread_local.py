"""Drop the read model's hosted readings from the bench books' caches, so the next build
reads those lines with the local model: the bench then measures the reader the build runs.

Each book's `stages/third-reading.json` is copied to `third-reading.hosted-backup.json`
first (once); lines listed under `via` are removed from the cache with their `via` entry.

    uv run python experiments/reread_local.py [--dry-run]
"""

import json
import shutil
import sys
from pathlib import Path

from roboscriptorium import bench
from roboscriptorium.files import write_atomic

BOOKS = sorted(
    {s.split(":")[0] for name in ("tuning", "validation") for s in bench.SETS[name]} | {"stella"}
)

total = 0
for book in BOOKS:
    path = Path("work") / book / "stages" / "third-reading.json"
    if not path.exists():
        continue
    raw = json.loads(path.read_text())
    hosted = {k for keys in raw.get("via", {}).values() for k in keys}
    total += len(hosted)
    print(f"{book[:40]:40} {len(raw['lines']):5} lines, {len(hosted):5} hosted")
    if "--dry-run" in sys.argv or not hosted:
        continue
    backup = path.with_name("third-reading.hosted-backup.json")
    if not backup.exists():
        shutil.copy2(path, backup)
    raw["lines"] = {k: v for k, v in raw["lines"].items() if k not in hosted}
    raw.pop("via")
    write_atomic(path, json.dumps(raw, ensure_ascii=False))
print(f"{total} lines to read again, ~{total * 1.4 / 3600:.1f} h at 1.4 s a line")
