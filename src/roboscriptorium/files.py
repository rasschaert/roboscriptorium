"""Writing the per-book caches."""

import functools
import hashlib
import inspect
import json
import os
import sys
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


def load_json(path: Path):
    """A cache file's JSON, or None when it is missing or can't be read: emptied or cut
    short by a crash, it is made again like a missing one."""
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        return None


@functools.cache
def code_stamp(module: str) -> str:
    """A short hash of a module's source and of the project's functions and modules it
    imports by name, one level deep (a helper they call in turn is not seen). A cache
    keyed by it (`read_cache(..., code=code_stamp(__name__))`) is made again whenever
    that code changes, and an old one is served again when a change is reverted."""
    mod = sys.modules[module]
    parts = [Path(mod.__file__).read_bytes()]
    for _, obj in sorted(vars(mod).items()):
        owner = obj.__name__ if inspect.ismodule(obj) else getattr(obj, "__module__", None)
        if not isinstance(owner, str) or owner == module or owner == __name__:
            continue
        if not owner.startswith("roboscriptorium"):
            continue
        if inspect.ismodule(obj):
            parts.append(Path(obj.__file__).read_bytes())
        elif inspect.isfunction(obj):
            parts.append(inspect.getsource(obj).encode())
    return hashlib.sha256(b"\0".join(parts)).hexdigest()[:12]


def read_cache(path: Path, version: int, **identity) -> dict | None:
    """A versioned JSON cache, when its format `version` and each `identity` field (the
    model, prompt or language it was made with, the code that measured it) match; else
    None, for it to be made again. A file a crash left unreadable counts as missing."""
    raw = load_json(path)
    if not isinstance(raw, dict) or raw.get("version") != version:
        return None
    if any(raw.get(k) != v for k, v in identity.items()):
        return None
    return raw


def write_cache(
    path: Path, version: int, payload: dict, indent: int | None = None, **identity
) -> None:
    """Write a versioned JSON cache whole (`write_atomic`): its version, its `identity`
    fields and its `payload`'s, as `read_cache` reads them."""
    blob = {"version": version, **identity, **payload}
    write_atomic(path, json.dumps(blob, ensure_ascii=False, indent=indent))


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
    seen = load_json(stamp)
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
