from pathlib import Path

import pytest

from roboscriptorium.golden import manifest
from roboscriptorium.golden.manifest import Golden, Scan, fetch


def _golden(scan: Scan) -> Golden:
    return Golden("book", "Title", "Author", "en", None, None, [scan])  # type: ignore[arg-type]


def _fake_download(contents: dict[str, bytes], fetched: list[str]):
    def download(url: str, path: Path) -> None:
        fetched.append(url)
        path.write_bytes(contents[url.rsplit("/", 1)[-1]])

    return download


def test_the_scans_internet_archive_files_are_read_from_the_manifest():
    scan = Golden.load("the-nature-of-a-crime").scan("doubleday-1924")
    assert scan.ia_item == "natureofcrime0000conr"
    assert "natureofcrime0000conr_jp2.zip" in dict(scan.ia_files)


def test_fetch_puts_the_internet_archive_files_beside_the_scan(tmp_path, monkeypatch):
    contents = {"x.pdf": b"pdf", "item_jp2.zip": b"pages", "item_abbyy.gz": b"ocr"}
    digest = {name: manifest.hashlib.sha256(data).hexdigest() for name, data in contents.items()}
    scan = Scan(
        "s",
        digest["x.pdf"],
        (1, 2),
        None,
        "https://example.org/x.pdf",
        None,
        ia_files=(
            ("item_jp2.zip", digest["item_jp2.zip"]),
            ("item_abbyy.gz", digest["item_abbyy.gz"]),
        ),
        ia_item="item",
    )
    fetched: list[str] = []
    monkeypatch.setattr(manifest, "_download", _fake_download(contents, fetched))

    book_dir = fetch(_golden(scan), scan, tmp_path)

    assert (book_dir / "ia" / "item_jp2.zip").read_bytes() == b"pages"
    assert "https://archive.org/download/item/item_abbyy.gz" in fetched
    fetch(_golden(scan), scan, tmp_path)
    assert len(fetched) == 3  # a second fetch downloads nothing


def test_fetch_refuses_an_internet_archive_file_that_changed(tmp_path, monkeypatch):
    contents = {"x.pdf": b"pdf", "item_jp2.zip": b"other pages"}
    scan = Scan(
        "s",
        manifest.hashlib.sha256(b"pdf").hexdigest(),
        (1, 2),
        None,
        "https://example.org/x.pdf",
        None,
        ia_files=(("item_jp2.zip", "0" * 64),),
        ia_item="item",
    )
    monkeypatch.setattr(manifest, "_download", _fake_download(contents, []))

    with pytest.raises(ValueError, match="item_jp2.zip"):
        fetch(_golden(scan), scan, tmp_path)
