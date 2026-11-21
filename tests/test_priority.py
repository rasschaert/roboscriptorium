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
    monkeypatch.setattr(priority, "_stopped", lambda pids: set())
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


def test_a_windows_own_process_is_left_running(monkeypatch):
    listing = "\t100.robo-bench\t(Detached)\n"
    ps = "100 1\n101 100\n102 101\n103 102\n"
    outputs = iter([listing, ps])
    monkeypatch.setattr(
        priority.subprocess,
        "run",
        lambda *a, **k: type("R", (), {"stdout": next(outputs)})(),
    )
    pids, names = priority._agent_processes()
    assert sorted(pids) == [102, 103]
    assert names == ["robo-bench"]


def test_a_run_already_stopped_stays_stopped_after_the_users_build(monkeypatch, tmp_path):
    sent = []
    monkeypatch.setattr(priority, "MARKER", tmp_path / "user-active")
    monkeypatch.setattr(priority, "_agent_processes", lambda: ([50, 51], ["robo-cols-chain"]))
    # 51 held by the battery guard, or paused by hand for the user's call.
    monkeypatch.setattr(priority, "_stopped", lambda pids: {51})
    monkeypatch.setattr(priority.os, "kill", lambda pid, sig: sent.append((pid, sig)))
    monkeypatch.delenv("STY", raising=False)
    monkeypatch.delenv("ROBO_AGENT", raising=False)
    with priority.first("build"):
        pass
    assert sent == [(50, signal.SIGSTOP), (50, signal.SIGCONT)]


def test_stopped_processes_are_told_from_running_ones():
    import subprocess

    sleeper = subprocess.Popen(["sleep", "30"])
    try:
        assert priority._stopped([sleeper.pid]) == set()
        sleeper.send_signal(signal.SIGSTOP)
        import time

        time.sleep(0.2)
        assert priority._stopped([sleeper.pid]) == {sleeper.pid}
    finally:
        sleeper.kill()


def test_the_guard_holds_the_runs_while_the_disk_is_nearly_full(monkeypatch, tmp_path):
    sent, frees = [], iter([40, 3, 10, 20])
    monkeypatch.setattr(priority, "HELD", tmp_path / "battery-held")
    monkeypatch.setattr(priority, "battery", lambda: 90)
    monkeypatch.setattr(priority, "disk_free", lambda: next(frees))
    monkeypatch.setattr(priority, "_agent_processes", lambda skip="": ([50], ["robo-bench"]))
    monkeypatch.setattr(priority.os, "kill", lambda pid, sig: sent.append(sig))
    held = []

    def tick(_):
        held.append((tmp_path / "battery-held").exists())
        if len(held) == 4:
            raise StopIteration

    monkeypatch.setattr(priority.time, "sleep", tick)
    try:
        priority.guard()
    except StopIteration:
        pass
    # 40 GB runs, 3 GB stops, 10 GB still waits for 15, 20 GB continues.
    assert held == [False, True, True, False]
    assert sent[-1] == signal.SIGCONT and signal.SIGSTOP in sent
