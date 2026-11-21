import os

import pytest

from roboscriptorium.files import SourceChanged, check_source, write_atomic


def test_a_cache_written_into_a_book_without_stages_makes_the_directory(tmp_path):
    write_atomic(tmp_path / "stages" / "textlayer.json", "{}")
    assert (tmp_path / "stages" / "textlayer.json").read_text() == "{}"


def test_bytes_are_written_whole(tmp_path):
    path = tmp_path / "model.pkl"
    write_atomic(path, b"\x00\x01")
    assert path.read_bytes() == b"\x00\x01"
    assert not path.with_name("model.pkl.partial").exists()


def test_a_log_whose_last_line_was_cut_off_is_read_and_appended_to_cleanly(tmp_path):
    from roboscriptorium.files import append_jsonl, read_jsonl

    log = tmp_path / "log.jsonl"
    log.write_text('{"n": 1}\n{"n": 2}\n{"n": 3, "cut')
    assert read_jsonl(log) == [{"n": 1}, {"n": 2}]
    append_jsonl(log, {"n": 4})
    assert read_jsonl(log) == [{"n": 1}, {"n": 2}, {"n": 4}]
    assert read_jsonl(tmp_path / "none.jsonl") == []


def test_a_broken_line_before_the_end_is_an_error(tmp_path):
    import json

    import pytest

    from roboscriptorium.files import read_jsonl

    log = tmp_path / "log.jsonl"
    log.write_text('{"n": 1\n{"n": 2}\n')
    with pytest.raises(json.JSONDecodeError):
        read_jsonl(log)


def test_a_replaced_source_is_refused_until_its_caches_are_moved_aside(tmp_path):
    source, stamp = tmp_path / "source.pdf", tmp_path / "stages" / "source.json"
    source.write_bytes(b"scan one")
    check_source(source, stamp)
    check_source(source, stamp)
    # Touched but the same file: still accepted.
    os.utime(source, (1, 1))
    check_source(source, stamp)
    source.write_bytes(b"scan two")
    with pytest.raises(SourceChanged):
        check_source(source, stamp)
    stamp.unlink()
    check_source(source, stamp)


def test_a_cache_is_read_back_only_with_its_version_and_identity(tmp_path):
    from roboscriptorium.files import read_cache, write_cache

    path = tmp_path / "c.json"
    assert read_cache(path, 1) is None
    write_cache(path, 2, {"lines": {"a": "één"}}, model="m", prompt="p")
    assert read_cache(path, 2, model="m", prompt="p")["lines"] == {"a": "één"}
    assert read_cache(path, 1, model="m", prompt="p") is None
    assert read_cache(path, 2, model="other", prompt="p") is None
    path.write_text("[1, 2]")  # a cache of an older shape
    assert read_cache(path, 2) is None


def test_a_cache_a_crash_left_empty_or_cut_short_counts_as_missing(tmp_path):
    from roboscriptorium.files import load_json, read_cache, write_cache

    path = tmp_path / "c.json"
    write_cache(path, 1, {"lines": {"a": "b"}})
    whole = path.read_text()
    for broken in ("", whole[: len(whole) // 2], "\x00\x00\x00"):
        path.write_text(broken)
        assert load_json(path) is None
        assert read_cache(path, 1) is None
    assert load_json(tmp_path / "none.json") is None


def _module(tmp_path, name, text):
    import importlib.util
    import sys

    path = tmp_path / f"{name}.py"
    path.write_text(text)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_the_code_stamp_follows_the_measuring_code_and_comes_back_when_it_is_reverted(
    tmp_path, monkeypatch
):
    import sys

    from roboscriptorium.files import code_stamp

    monkeypatch.syspath_prepend(str(tmp_path))
    original = "def measure(x):\n    return x\n"
    _module(tmp_path, "roboscriptorium_tmp_measure", original)
    first = code_stamp("roboscriptorium_tmp_measure")
    _module(tmp_path, "roboscriptorium_tmp_measure", "def measure(x):\n    return 2 * x\n")
    code_stamp.cache_clear()
    assert code_stamp("roboscriptorium_tmp_measure") != first
    _module(tmp_path, "roboscriptorium_tmp_measure", original)
    code_stamp.cache_clear()
    assert code_stamp("roboscriptorium_tmp_measure") == first
    del sys.modules["roboscriptorium_tmp_measure"]
    code_stamp.cache_clear()


def test_the_code_stamp_sees_a_helper_imported_from_another_project_module(tmp_path, monkeypatch):
    import sys

    from roboscriptorium.files import code_stamp

    monkeypatch.syspath_prepend(str(tmp_path))
    user = "from roboscriptorium_tmp_helper import gap\n\ndef measure(x):\n    return gap(x)\n"
    _module(tmp_path, "roboscriptorium_tmp_helper", "def gap(x):\n    return x\n")
    _module(tmp_path, "roboscriptorium_tmp_user", user)
    first = code_stamp("roboscriptorium_tmp_user")
    _module(tmp_path, "roboscriptorium_tmp_helper", "def gap(x):\n    return x + 1\n")
    _module(tmp_path, "roboscriptorium_tmp_user", user)
    code_stamp.cache_clear()
    assert code_stamp("roboscriptorium_tmp_user") != first
    for name in ("roboscriptorium_tmp_helper", "roboscriptorium_tmp_user"):
        del sys.modules[name]
    code_stamp.cache_clear()
