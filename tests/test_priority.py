import signal

from roboscriptorium import priority

LISTING = """There are screens on:
\t41635.robo-cols-chain\t(Detached)
\t26404.robo-books-render\t(Detached)
\t999.other-session\t(Detached)
3 Sockets in /var/folders/x.
"""


def test_the_agents_sessions_and_every_process_below_them_are_found():
    assert priority.sessions(LISTING) == {41635: "robo-cols-chain", 26404: "robo-books-render"}
    table = [(1, 0), (41635, 1), (50, 41635), (51, 50), (52, 51), (60, 999), (70, 1)]
    assert sorted(priority.descendants({41635}, table)) == [50, 51, 52]


def test_the_users_build_pauses_the_agents_runs_and_the_agents_own_passes(monkeypatch, tmp_path):
    sent = []
    monkeypatch.setattr(priority, "MARKER", tmp_path / "user-active")
    monkeypatch.setattr(priority, "_agent_processes", lambda: ([50, 51], ["robo-cols-chain"]))
    monkeypatch.setattr(priority.os, "kill", lambda pid, sig: sent.append((pid, sig)))
    monkeypatch.delenv("STY", raising=False)
    monkeypatch.delenv("ROBO_AGENT", raising=False)
    with priority.first("build"):
        assert sent == [(50, signal.SIGSTOP), (51, signal.SIGSTOP)]
        assert (tmp_path / "user-active").exists()
    assert sent[2:] == [(50, signal.SIGCONT), (51, signal.SIGCONT)]
    assert not (tmp_path / "user-active").exists()
    # A build that fails still lets the agent's runs go on.
    sent.clear()
    try:
        with priority.first("build"):
            raise RuntimeError("build failed")
    except RuntimeError:
        pass
    assert sent[2:] == [(50, signal.SIGCONT), (51, signal.SIGCONT)]
    # Inside the agent's own session nothing is paused.
    sent.clear()
    monkeypatch.setenv("STY", "41635.robo-cols-chain")
    with priority.first("build"):
        pass
    assert sent == []


def test_hold_stops_under_the_floor_and_waits_for_the_resume_level():
    assert not priority.hold(31, held=False)
    assert priority.hold(29, held=False)
    assert priority.hold(45, held=True)
    assert not priority.hold(50, held=True)
    assert not priority.hold(None, held=True)
