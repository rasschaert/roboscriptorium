from roboscriptorium.files import write_atomic


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
