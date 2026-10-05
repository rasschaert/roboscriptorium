"""Golden books: public-domain scans paired with a human-checked reference text.

Each lives in `golden/<name>/` (in git): `manifest.toml`, the derived reference
chapters in `text/`, and `PROVENANCE.md`. Scans are fetched into
`work/<name>--<scan id>/`, which is an ordinary book directory.
"""

import hashlib
import shutil
import tomllib
from dataclasses import dataclass
from pathlib import Path

import httpx

GOLDEN_ROOT = Path("golden")


@dataclass(frozen=True)
class Scan:
    id: str
    sha256: str
    body_pages: tuple[int, int]
    cover_page: int | None
    url: str | None  # None when it can only be placed by hand
    source: str | None  # where a human can get it


@dataclass(frozen=True)
class Golden:
    name: str
    title: str
    author: str
    language: str
    repo: str
    commit: str
    scans: list[Scan]

    @property
    def root(self) -> Path:
        return GOLDEN_ROOT / self.name

    @property
    def text_dir(self) -> Path:
        return self.root / "text"

    def scan(self, scan_id: str) -> Scan:
        return next(s for s in self.scans if s.id == scan_id)

    def book_dir(self, scan: Scan, work: Path = Path("work")) -> Path:
        return work / f"{self.name}--{scan.id}"

    @classmethod
    def load(cls, name: str) -> "Golden":
        with (GOLDEN_ROOT / name / "manifest.toml").open("rb") as f:
            data = tomllib.load(f)
        scans = [
            Scan(
                id=s["id"],
                sha256=s["sha256"],
                body_pages=tuple(s["body_pages"]),
                cover_page=s.get("cover_page"),
                url=s.get("url"),
                source=s.get("source"),
            )
            for s in data["scans"]
        ]
        ref = data["reference"]
        return cls(
            name, data["title"], data["author"], data["language"], ref["repo"], ref["commit"], scans
        )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(golden: Golden, scan: Scan, work: Path = Path("work")) -> Path:
    """Put the scan and a book.toml in its book directory; return that directory."""
    book_dir = golden.book_dir(scan, work)
    book_dir.mkdir(parents=True, exist_ok=True)
    pdf = book_dir / "source.pdf"

    if not pdf.exists():
        if scan.url is None:
            raise FileNotFoundError(
                f"{scan.id} can't be downloaded; get it from {scan.source} and save it as {pdf}"
            )
        partial = pdf.with_suffix(".part")
        with httpx.stream("GET", scan.url, follow_redirects=True, timeout=120) as resp:
            resp.raise_for_status()
            with partial.open("wb") as f:
                for chunk in resp.iter_bytes():
                    f.write(chunk)
        shutil.move(partial, pdf)

    if (actual := sha256(pdf)) != scan.sha256:
        raise ValueError(f"{pdf}: sha256 {actual}, expected {scan.sha256}")

    first, last = scan.body_pages
    cover = f"cover_page = {scan.cover_page}\n" if scan.cover_page else ""
    (book_dir / "book.toml").write_text(
        f'title = "{golden.title}"\n'
        f'author = "{golden.author}"\n'
        f'language = "{golden.language}"\n'
        f"{cover}"
        f"body_pages = [{first}, {last}]\n"
        f'golden = "{golden.name}"\n'
    )
    return book_dir
