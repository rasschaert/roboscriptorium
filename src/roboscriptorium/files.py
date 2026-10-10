"""Writing the per-book caches."""

import json
import os
from pathlib import Path


def write_atomic(path: Path, text: str | bytes) -> None:
    """Write a file whole or not at all: an interrupted run leaves the old one. The
    directory is made if it isn't there."""
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    if isinstance(text, bytes):
        partial.write_bytes(text)
    else:
        partial.write_text(text)
    os.replace(partial, path)


def read_jsonl(path: Path) -> list[dict]:
    """The entries of an append-only log, one JSON object a line. A last line cut off by
    an interrupted write is skipped; a broken line anywhere else is an error."""
    if not path.exists():
        return []
    lines = path.read_text().splitlines()
    out = []
    for n, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            if any(rest.strip() for rest in lines[n + 1 :]):
                raise
            break
    return out


def append_jsonl(path: Path, entry: dict) -> None:
    """One more line of an append-only log. A last line cut off by an interrupted write
    is dropped first (it can't be read), so the new one stands alone."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab+") as f:
        f.seek(0)
        data = f.read()
        if data and not data.endswith(b"\n"):
            f.seek(0)
            f.truncate(data.rfind(b"\n") + 1)
        f.write((json.dumps(entry, ensure_ascii=False) + "\n").encode())
