import json

from roboscriptorium import bench, errorlog
from roboscriptorium.disagreements import Disagreement
from roboscriptorium.pdf import Line, PageText


def _error(got, want, key="k", lines=(0, 0)):
    return Disagreement(key, got, want, "een twee drie vier vijf", "zes zeven", 9, lines)


def test_an_errors_origin_says_whether_the_layer_already_read_it_so():
    page = PageText(9, 300, 500, [Line("Hij zei het tegen hem.", 20, 20, 280, 30)])
    pages = {9: page}
    assert errorlog.layer_origin(_error("tegen", "togen"), pages) == "kept"
    assert errorlog.layer_origin(_error("tegcn", "tegen"), pages) == "made"
    assert errorlog.layer_origin(_error("", "tegen"), pages) == "lost"
    assert errorlog.layer_origin(_error("nergens", "ergens"), pages) == "unclear"


def test_a_diff_keys_errors_by_book_and_place_over_the_books_both_runs_scored():
    def row(book, key, size=1):
        shown = {"page": 9, "got": "a", "want": "b", "before": "", "after": ""}
        return {"book": book, "key": key, "size": size, "asked": False, "kind": "letters",
                "layer": "kept", **shown}  # fmt: skip

    old = [row("a", "1"), row("a", "2"), row("gone", "9")]
    new = [row("a", "2"), row("a", "3", size=2), row("new", "7")]
    d = errorlog.diff(old, new)
    assert [r["key"] for r in d.fixed] == ["1"]
    assert [r["key"] for r in d.made] == ["3"]
    assert [(a["key"], b["key"]) for a, b in d.kept] == [("2", "2")]
    assert errorlog.report(d)[0].startswith("fixed 1 wrong words (1 unasked), made 2")


def test_bench_saves_the_error_rows_beside_the_record_and_not_in_it(tmp_path):
    rows = [{"book": "a", "key": "k", "size": 1}]
    record = {"set": "quick", "commit": "abc", "books": {"a": {"spec": "a", "_errors": rows}}}
    path = bench.save(record, tmp_path)
    assert "_errors" not in json.loads(path.read_text())["books"]["a"]
    assert errorlog.load(path) == rows
    assert errorlog.load(tmp_path / "other.json") == []


def test_each_cause_is_told_from_its_neighbours():
    cases = {
        ("zijn", "zíjn"): "stress accent",
        ("hé?'", "hè?'"): "stress accent",
        ("heroine", "heroïne"): "diaeresis",
        ("hygiéne", "hygiëne"): "other accent",
        ("ZOU", "zou"): "case",
        ("meteen", "met een"): "glued or split words",
        ("got,you", "got, you"): "glued or split words",
        ("I —'", "I—'"): "dash or dot spacing",
        ("blood-curdling", "bloodcurdling"): "compound hyphen",
        ("email", "e-mail"): "compound hyphen",
        ("dagen,", "dagen,'"): "quote missing or extra",
        ('"Your', "'Your"): "quote glyph",
        ("-'", "—'"): "dash",
        ("eraf'", "eraf.'"): "dots and stops",
        ("rood;", "rood,'"): "punctuation swapped",
        ("Tk", "Ik"): "letters misread",
        ("", "Móni"): "missing text",
        ("BAM!", ""): "extra text",
        ("phy- 35 sique.", "physique."): "words",
    }
    assert {k: errorlog.cause(*k) for k in cases} == cases


def test_causes_compare_page_by_page_over_the_pages_both_runs_scored():
    def row(page, cause, size=1):
        return {"book": "a", "key": f"{page}{cause}", "page": page, "size": size,
                "got": "x", "want": "y", "cause": cause}  # fmt: skip

    old = {"books": {"a": {"pages": {"1": [], "2": [], "3": []}}}}
    new = {"books": {"a": {"pages": {"1": [], "2": []}}}}
    rows_old = [row(1, "stress accent"), row(2, "stress accent"), row(3, "stress accent")]
    rows_new = [row(2, "diaeresis", 2)]
    table = {c: (b, a) for c, b, a, *_ in bench.by_cause(old, new, rows_old, rows_new)}
    assert table == {"stress accent": (1.0, 0.0), "diaeresis": (0.0, 1.0)}
