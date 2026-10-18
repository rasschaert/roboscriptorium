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
