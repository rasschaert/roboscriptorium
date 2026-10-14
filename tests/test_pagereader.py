import json

from roboscriptorium import pagereader
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import Line, PageText


def _page(*texts: str) -> PageText:
    return PageText(
        1, 400, 600, [Line(t, 0, 20 * k, 300, 20 * k + 12) for k, t in enumerate(texts)]
    )


PAGE = _page(
    "Het was muf en vochtig in de keuken, het meest",
    "liefdeloze vertrek in het huis. Nog geen twee voorwer-",
    "pen pasten bij elkaar. De ouderwetse koelkast",
    "liet een scheet telkens wanneer je de deur opende.",
)


def test_a_reading_the_layer_agrees_with_gives_each_line_its_own_text():
    reading = "\n".join(line.text for line in PAGE.lines)
    assert pagereader.split_lines(PAGE, reading) == {k: ln.text for k, ln in enumerate(PAGE.lines)}


def test_a_word_read_whole_is_split_where_the_layer_breaks_it():
    reading = (
        "Het was muf en vochtig in de keuken, het meest liefdeloze vertrek in het huis. "
        "Nog geen twee voorwerpen pasten bij elkaar. De ouderwetse koelkast liet een scheet "
        "telkens wanneer je de deur opende."
    )
    got = pagereader.split_lines(PAGE, reading)
    assert got[1].endswith("twee voorwer-") and got[2].startswith("pen pasten")


def test_a_hyphen_the_reader_keeps_in_the_word_is_not_doubled():
    page = _page("een verschoten Church Lady-", "T-shirt omhoog gehouden")
    got = pagereader.split_lines(page, "een verschoten Church Lady-T-shirt omhoog gehouden")
    assert got == {0: "een verschoten Church Lady-", 1: "T-shirt omhoog gehouden"}


def test_a_difference_lands_on_its_own_line():
    reading = "\n".join(line.text for line in PAGE.lines).replace("koelkast", "koeIkast")
    got = pagereader.split_lines(PAGE, reading)
    assert got[2] == "pen pasten bij elkaar. De ouderwetse koeIkast"
    assert got[3] == PAGE.lines[3].text


def test_a_dash_the_layer_lost_costs_one_word_and_keeps_its_neighbours_on_their_lines():
    page = _page("it down. This is interesting very interesting", "something quite new.")
    reading = "it down. This is interesting—very interesting—something quite new."
    got = pagereader.split_lines(page, reading)
    assert got == {0: "it down. This is interesting—very interesting—", 1: "something quite new."}


def test_a_running_head_the_layer_lacks_is_left_out_but_a_lost_word_is_kept():
    reading = "THE STORY OF DOCTOR DOLITTLE\n" + "\n".join(ln.text for ln in PAGE.lines)
    got = pagereader.split_lines(PAGE, reading)
    assert got[0] == PAGE.lines[0].text
    page = _page("Het was muf en in de keuken")
    assert pagereader.split_lines(page, "Het was muf en vochtig in de keuken") == {
        0: "Het was muf en vochtig in de keuken"
    }


def test_a_reading_of_another_page_reads_no_line():
    assert pagereader.split_lines(PAGE, "Een heel andere bladzijde met andere woorden.") == {}


def test_markdown_and_a_repeat_are_not_read_as_words():
    assert [w for w, _ in pagereader.reading_words("# Hoofdstuk *een*\n\nHet was")] == [
        "Hoofdstuk",
        "een",
        "Het",
        "was",
    ]
    page = "Het was muf en vochtig in de keuken, het meest liefdeloze vertrek in het huis.\n"
    assert pagereader.once(page + page[:70]) == page


def test_pages_are_read_once_and_only_checked_lines_come_back(tmp_path, monkeypatch):
    import pymupdf

    doc = pymupdf.open()
    doc.new_page(width=400, height=600)
    doc.save(tmp_path / "source.pdf")
    calls = []

    def read(png, model, url):
        calls.append(model)
        return "\n".join(ln.text for ln in PAGE.lines).replace("muf", "rnuf")

    monkeypatch.setattr(pagereader, "read_page", read)
    cache = tmp_path / "page-reading.json"
    args = (tmp_path / "source.pdf", [PAGE], {SourceRef(1, 0), SourceRef(1, 3)}, "glm-ocr:bf16", "")
    got = pagereader.line_readings(*args, cache)
    assert got == {
        SourceRef(1, 0): "Het was rnuf en vochtig in de keuken, het meest",
        SourceRef(1, 3): PAGE.lines[3].text,
    }
    assert pagereader.line_readings(*args, cache) == got and calls == ["glm-ocr:bf16"]
    assert json.loads(cache.read_text())["pixels"] == pagereader.PIXELS
