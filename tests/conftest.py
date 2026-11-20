import os

import pytest

from roboscriptorium import hyphens, pipeline
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
    # The line-role trees are trained on the books in work/, which a test can't depend
    # on: tests run on the rules, and a test of the trees switches them on itself.
    monkeypatch.setenv("ROBO_SORTER", "0")
    monkeypatch.setenv("ROBO_SORTER_SECOND", "")
    # The same for the italic trees: tests run on the slant cuts.
    monkeypatch.setenv("ROBO_ITALIC_TREES", "0")
    # The hyphen panel and its learned decision likewise: tests run on the judge alone.
    monkeypatch.setenv("ROBO_HYPHEN_JUDGES", "")
    monkeypatch.setenv("ROBO_HYPHEN_LEARNED", "")
    # No font folder: the judge `render` is left out, as on a machine without the
    # fonts. A test of it makes its own judge.
    monkeypatch.setenv("ROBO_FONTS", "no-fonts-in-tests")
    # One process: a test's stand-ins don't reach the bench's worker processes.
    monkeypatch.setenv("ROBO_BENCH_WORKERS", "1")
    # A closed port: a model call a test forgot to stub fails at once instead of reaching
    # the machine's Ollama and loading a model.
    monkeypatch.setenv("ROBO_OLLAMA_URL", "http://127.0.0.1:9")


@pytest.fixture(autouse=True)
def _own_judge_lock(monkeypatch, tmp_path):
    """A lock of the test's own: a bench asking the hyphen judges holds the machine's."""
    monkeypatch.setattr(hyphens, "JUDGE_LOCK", tmp_path / "hyphen-judges.lock")


@pytest.fixture(autouse=True)
def _no_pause_of_live_runs(monkeypatch, request):
    """A test's build pauses no real run: `priority.first` finds no agent processes, so a
    test of the `build` command doesn't stop and continue the machine's `robo-*` jobs.
    The tests of `priority` itself set what it finds."""
    if request.module.__name__.endswith("test_priority"):
        return
    from roboscriptorium import priority

    monkeypatch.setattr(priority, "_agent_processes", lambda skip="": ([], []))
