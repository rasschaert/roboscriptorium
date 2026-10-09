from roboscriptorium.files import write_atomic


def test_a_cache_written_into_a_book_without_stages_makes_the_directory(tmp_path):
    write_atomic(tmp_path / "stages" / "textlayer.json", "{}")
    assert (tmp_path / "stages" / "textlayer.json").read_text() == "{}"


def test_bytes_are_written_whole(tmp_path):
    path = tmp_path / "model.pkl"
    write_atomic(path, b"\x00\x01")
    assert path.read_bytes() == b"\x00\x01"
    assert not path.with_name("model.pkl.partial").exists()
