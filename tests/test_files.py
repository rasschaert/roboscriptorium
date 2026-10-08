from roboscriptorium.files import write_atomic


def test_a_cache_written_into_a_book_without_stages_makes_the_directory(tmp_path):
    write_atomic(tmp_path / "stages" / "textlayer.json", "{}")
    assert (tmp_path / "stages" / "textlayer.json").read_text() == "{}"
