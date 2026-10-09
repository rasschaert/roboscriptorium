import os

import pytest

from roboscriptorium import pipeline
from roboscriptorium.lexicon import Lexicon


@pytest.fixture(autouse=True)
def _no_word_list_on_disk(monkeypatch):
    """The pipeline's word list is an empty one: tests never unpack tesseract's model
    into work/. A test that needs words passes its own `Lexicon`."""
    monkeypatch.setattr(pipeline.Lexicon, "load", lambda lang: Lexicon(set()))


@pytest.fixture(autouse=True)
def _default_settings(monkeypatch):
    """Tests run on the defaults in `config.py`: the developer's shell can't change a
    model, switch the arbiter off or route a call to a hosted model. A test that needs a
    setting sets it itself."""
    for name in list(os.environ):
        if name.startswith("ROBO_") or name == "OPENROUTER_API_KEY":
            monkeypatch.delenv(name)
