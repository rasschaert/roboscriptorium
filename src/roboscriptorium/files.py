"""Writing the per-book caches."""

import hashlib
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


class SourceChanged(Exception):
    """The book's source file isn't the one its caches were built from."""


def check_source(source: Path, stamp: Path) -> None:
    """Refuse a source that differs from the one `stamp` records, the first time it
    records it. No cache names the file it was built from, so a replaced source would
    otherwise be read from the old one's caches. Size and mtime spare the hash when
    nothing was touched."""
    stat = source.stat()
    seen = json.loads(stamp.read_text()) if stamp.exists() else None
    if seen and (seen["size"], seen["mtime"]) == (stat.st_size, stat.st_mtime):
        return
    digest = _sha256(source)
    if seen and seen["sha256"] != digest:
        raise SourceChanged(
            f"{source} isn't the file the caches in {stamp.parent} were built from: "
            "move that folder aside to build from the new one"
        )
    entry = {"sha256": digest, "size": stat.st_size, "mtime": stat.st_mtime}
    write_atomic(stamp, json.dumps(entry))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()
