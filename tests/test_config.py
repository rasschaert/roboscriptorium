import pytest

from roboscriptorium.config import Settings


@pytest.mark.parametrize("value, on", [("0", False), ("off", False), ("False", False), ("1", True)])
def test_learned_trust_is_switched_by_its_variable(monkeypatch, value, on):
    monkeypatch.setenv("ROBO_OCR_TRUST", value)
    assert Settings.from_env().ocr_trust is on


def test_an_unknown_switch_value_is_refused(monkeypatch):
    monkeypatch.setenv("ROBO_OCR_TRUST", "nope")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_a_hosted_reader_needs_a_local_one_to_stand_in_for(monkeypatch):
    monkeypatch.setenv("ROBO_READ_MODEL", "")
    monkeypatch.setenv("ROBO_READ_VIA", "openrouter:m@p")
    with pytest.raises(ValueError):
        Settings.from_env()


@pytest.mark.parametrize("value", ["0", "1.5", "-0.2"])
def test_the_ask_threshold_must_be_a_probability(monkeypatch, value):
    monkeypatch.setenv("ROBO_OCR_ASK_BELOW", value)
    with pytest.raises(ValueError):
        Settings.from_env()


def test_a_question_budget_below_zero_is_refused(monkeypatch):
    monkeypatch.setenv("ROBO_OCR_QUESTIONS", "-1")
    with pytest.raises(ValueError):
        Settings.from_env()


def test_two_judges_by_one_name_are_refused(monkeypatch):
    monkeypatch.setenv("ROBO_JUDGE_MODEL", "clef:27b")
    monkeypatch.setenv("ROBO_CHECK_MODEL", "clef:27b")
    with pytest.raises(ValueError):
        Settings.from_env()
