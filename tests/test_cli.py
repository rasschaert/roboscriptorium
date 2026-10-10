import pytest
import typer

from roboscriptorium.cli import _range


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
