"""Golden books: public-domain scans paired with a human-checked reference text.

Each lives in `golden/<name>/` (in git): `manifest.toml`, the reference chapters
derived from a Project Gutenberg transcription in `text/`, and `PROVENANCE.md`.
`standard-ebooks/` holds the Standard Ebooks text, kept for later style work. Scans are fetched into
`work/<name>--<scan id>/`, which is an ordinary book directory.

A book still under copyright in the EU keeps only its manifest in git; its
reference text, provenance and verdicts live in `work/golden/<name>/`.
"""

import hashlib
import json
import shutil
import tomllib
from dataclasses import dataclass
from pathlib import Path

import httpx

GOLDEN_ROOT = Path("golden")
PRIVATE_ROOT = Path("work/golden")


@dataclass(frozen=True)
class Scan:
    id: str
    sha256: str
    body_pages: tuple[int, int]
    cover_page: int | None
    url: str | None  # None when it can only be placed by hand
    source: str | None  # where a human can get it


@dataclass(frozen=True)
class Gutenberg:
    ebook: int
    url: str
    chapters: tuple[str, str]  # first lines of the first and last chapter headings


@dataclass(frozen=True)
class PublisherEpub:
    source: str  # edition and ISBN, for humans
    sha256: str
    files: tuple[str, ...]  # content files to read, in order
    heading_prefixes: tuple[str, ...]  # classes of paragraphs that are headings
    italic_classes: frozenset[str] = frozenset()  # classes that set text in italics
    roman_classes: frozenset[str] = frozenset()  # classes that set it upright again
    blank_classes: frozenset[str] = frozenset()  # paragraphs that stand for a blank line
    note_classes: frozenset[str] = frozenset()  # footnotes, kept apart from the text
    # The print's dash where the EPUB sets a spaced hyphen-minus ("" keeps the hyphen).
    hyphen_dash: str = ""
    # A heading set as an image: a regex on the image's alt text whose group 1 is the
    # heading as printed ("Chapter Header, Chapter (\\d+)" gives "2").
    image_heading: str = ""


@dataclass(frozen=True)
class StandardEbooks:
    repo: str
    commit: str


@dataclass(frozen=True)
class Golden:
    name: str
    title: str
    author: str
    language: str
    reference: Gutenberg | PublisherEpub
    standard_ebooks: StandardEbooks | None
    scans: list[Scan]
    eu_copyright_until: int | None = None  # last year of EU copyright, if any

    @property
    def root(self) -> Path:
        return GOLDEN_ROOT / self.name

    @property
    def data_root(self) -> Path:
        """Where the reference text and verdicts live: in git only if public domain."""
        return PRIVATE_ROOT / self.name if self.eu_copyright_until else self.root

    @property
    def text_dir(self) -> Path:
        return self.data_root / "text"

    @property
    def notes_path(self) -> Path:
        return self.data_root / "notes.txt"

    @property
    def verdicts_dir(self) -> Path:
        return self.data_root / "verdicts"

    @property
    def se_dir(self) -> Path:
        return self.root / "standard-ebooks"

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
        reference = (
            Gutenberg(ref["gutenberg"], ref["url"], tuple(ref["chapters"]))
            if "gutenberg" in ref
            else PublisherEpub(
                ref["source"],
                ref["sha256"],
                tuple(ref["files"]),
                tuple(ref.get("heading_prefixes", ())),
                frozenset(ref.get("italic_classes", ())),
                frozenset(ref.get("roman_classes", ())),
                frozenset(ref.get("blank_classes", ())),
                frozenset(ref.get("note_classes", ())),
                ref.get("hyphen_dash", ""),
                ref.get("image_heading", ""),
            )
        )
        se = data.get("standard_ebooks")
        return cls(
            name,
            data["title"],
            data["author"],
            data["language"],
            reference,
            StandardEbooks(se["repo"], se["commit"]) if se else None,
            scans,
            data.get("eu_copyright_until"),
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
    # A JSON string is a valid TOML basic string, quotes and backslashes escaped.
    q = lambda s: json.dumps(s, ensure_ascii=False)  # noqa: E731
    (book_dir / "book.toml").write_text(
        f"title = {q(golden.title)}\n"
        f"author = {q(golden.author)}\n"
        f"language = {q(golden.language)}\n"
        f"{cover}"
        f"body_pages = [{first}, {last}]\n"
        f"golden = {q(golden.name)}\n"
    )
    return book_dir
