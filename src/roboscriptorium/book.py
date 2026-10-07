"""A book's working directory and its per-book settings (`book.toml`).

Layout of a book directory (always under the gitignored `work/`):

    work/<book>/
      book.toml       metadata, page ranges and typography a human settled
      source.pdf      the input
      stages/         resumable per-stage artefacts
      review/         a human's answers about flagged regions
      <book>.epub     the output
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Book:
    root: Path
    title: str
    author: str
    language: str
    source: Path
    cover_page: int | None
    # Inclusive, 1-based page range holding the running text.
    body_pages: tuple[int, int]
    # Name of the golden book under golden/ that this scan is scored against.
    golden: str | None = None
    # How the book prints its dashes: "–" or "—", and "none", "thin" or "word" spacing.
    # Unset, the pipeline measures it on the scan (`typography.py`).
    dash: str | None = None
    dash_spacing: str | None = None

    @classmethod
    def load(cls, root: Path) -> "Book":
        with (root / "book.toml").open("rb") as f:
            data = tomllib.load(f)
        first, last = data["body_pages"]
        return cls(
            root=root,
            title=data["title"],
            author=data["author"],
            language=data["language"],
            source=root / data.get("source", "source.pdf"),
            cover_page=data.get("cover_page"),
            body_pages=(first, last),
            golden=data.get("golden"),
            dash=data.get("dash"),
            dash_spacing=data.get("dash_spacing"),
        )

    @property
    def stages(self) -> Path:
        path = self.root / "stages"
        path.mkdir(exist_ok=True)
        return path

    @property
    def corrections_path(self) -> Path:
        return self.root / "review" / "regions.jsonl"

    @property
    def epub_path(self) -> Path:
        return self.root / f"{self.root.name}.epub"
