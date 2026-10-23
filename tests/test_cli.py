from pathlib import Path
from types import SimpleNamespace

import pytest
import typer

from roboscriptorium import cli
from roboscriptorium.cli import _range
from roboscriptorium.config import Settings


def test_a_page_range_takes_a_hyphen_an_en_dash_or_one_page():
    assert _range("9-64") == (9, 64)
    assert _range("9–64") == (9, 64)
    assert _range("7") == (7, 7)
    assert _range(None) is None


@pytest.mark.parametrize("value", ["7-", "-5", "64-9", "seven"])
def test_a_malformed_page_range_is_refused(value):
    with pytest.raises(typer.BadParameter):
        _range(value)


def test_pages_and_chapters_count_from_one():
    with pytest.raises(typer.BadParameter):
        _range("0-3")
    assert _range("1-3") == (1, 3)


def test_a_model_asked_through_tokens_is_recorded_by_its_ollama_digest(monkeypatch):
    tags = {"models": [{"name": "big-judge", "digest": "0123456789abcdef"}]}
    monkeypatch.setattr(cli.httpx, "get", lambda url, timeout: SimpleNamespace(json=lambda: tags))
    settings = Settings(check_model="tokens:big-judge", alarm_model="")
    assert cli._model_versions(settings)["tokens:big-judge"] == "0123456789ab"


def test_build_drafts_a_missing_book_toml_first(monkeypatch, tmp_path):
    from typer.testing import CliRunner

    monkeypatch.chdir(tmp_path)
    drafted = []

    def initialise(pdf, root, language=None):
        drafted.append((pdf, root))
        root.mkdir(parents=True, exist_ok=True)
        (root / "book.toml").write_text(
            'title = "T"\nauthor = "A"\nlanguage = "nl"\nbody_pages = [1, 2]\n'
        )
        return root / "book.toml"

    built = []
    monkeypatch.setattr(cli, "_initialise", initialise)
    monkeypatch.setattr(
        cli.pipeline,
        "build",
        lambda book, pages: built.append(book.root) or SimpleNamespace(blocks=[]),
    )
    monkeypatch.setattr(cli, "keep_dated", lambda *a: None)
    (tmp_path / "Mijn Boek.pdf").write_bytes(b"%PDF")
    result = CliRunner().invoke(cli.app, ["build", "Mijn Boek.pdf"])
    assert result.exit_code == 0, result.output
    assert drafted == [(Path("Mijn Boek.pdf"), Path("work/mijn-boek"))]
    assert built == [Path("work/mijn-boek")]
    # A folder with only its source is set up in place; one with a book.toml is left alone.
    (tmp_path / "boek").mkdir()
    (tmp_path / "boek" / "source.pdf").write_bytes(b"%PDF")
    assert CliRunner().invoke(cli.app, ["build", "boek"]).exit_code == 0
    assert CliRunner().invoke(cli.app, ["build", "boek"]).exit_code == 0
    assert drafted[1:] == [(Path("boek/source.pdf"), Path("boek"))]
    # Nothing to set up from: a clear error, not a traceback.
    assert CliRunner().invoke(cli.app, ["build", "leeg"]).exit_code != 0
