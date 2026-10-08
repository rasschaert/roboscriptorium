import pytest

from roboscriptorium import pipeline
from roboscriptorium.lexicon import Lexicon


@pytest.fixture(autouse=True)
def _no_word_list_on_disk(monkeypatch):
    """The pipeline's word list is an empty one: tests never unpack tesseract's model
    into work/. A test that needs words passes its own `Lexicon`."""
    monkeypatch.setattr(pipeline.Lexicon, "load", lambda lang: Lexicon(set()))
