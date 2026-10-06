"""Writing the per-book caches."""

import os
from pathlib import Path


def write_atomic(path: Path, text: str) -> None:
    """Write a file whole or not at all: an interrupted run leaves the old one."""
    partial = path.with_name(path.name + ".partial")
    partial.write_text(text)
    os.replace(partial, path)
