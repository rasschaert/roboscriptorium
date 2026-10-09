"""Writing the per-book caches."""

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
