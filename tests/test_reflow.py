from roboscriptorium.ir import Heading, Paragraph, SourceRef
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.reflow import join, reflow, tidy
from roboscriptorium.roles import LineRole

SPACING = 15.0
HEIGHT = 500.0


def page(number: int, rows: list[tuple[float, str]], footer: list[str] = ()) -> PageText:
    """Synthetic page: rows of (x0, text) from the top, footer lines at the bottom."""
    lines = [
        Line(text, x, 20 + i * SPACING, 250, 30 + i * SPACING) for i, (x, text) in enumerate(rows)
    ]
    for i, text in enumerate(footer):
        y = HEIGHT * 0.9 + i * SPACING
        lines.append(Line(text, 130, y, 140, y + 10))
    return PageText(number, 280, HEIGHT, lines)


def test_join_undoes_hyphenation_only_before_lowercase():
    assert join("af-", "stormde") == "afstormde"
    assert join("Noord-", "Holland") == "Noord-Holland"
    assert join("alles—", "en het") == "alles—en het"
    assert join("de", "kerk") == "de kerk"


def test_indent_starts_paragraph_and_footer_is_dropped():
    rows = [
        (10, "Eerste regel van de"),
        (10, "alinea."),
        (20, "Tweede alinea"),
        (10, "loopt door."),
    ]
    paragraphs = reflow([page(5, rows, footer=["><", "5"])])
    assert [p.text for p in paragraphs] == [
        "Eerste regel van de alinea.",
        "Tweede alinea loopt door.",
    ]
    assert paragraphs[0].opening and not paragraphs[1].opening


def test_paragraph_continues_across_page_break():
    first = page(10, [(10, "Een zin die door-")], footer=["Io"])
    second = page(11, [(10, "loopt op de volgende pagina."), (20, "Nieuwe alinea.")])
    paragraphs = reflow([first, second])
    assert paragraphs[0].text == "Een zin die doorloopt op de volgende pagina."
    assert [(s.page, s.line) for s in paragraphs[0].sources] == [(10, 0), (11, 0)]


def test_margin_follows_skew():
    # Line starts drift 1pt per line; only the 10pt jump is an indent.
    rows = [(10 + i, f"regel {i}") for i in range(8)]
    rows[5] = (25, "inspringing")
    paragraphs = reflow([page(5, rows)])
    assert len(paragraphs) == 2
    assert paragraphs[1].text.startswith("inspringing")


def test_roles_drop_artefacts_and_keep_blocks_in_page_order():
    rows = [
        (10, "20 SENSE AND SENSIBILITY."),
        (10, "einde van een zin."),
        (60, "CHAPTER"),
        (70, "V."),
        (10, "Begin van het hoofdstuk"),
        (10, "dat doorloopt."),
    ]
    not_body = {0: "running_head", 2: "chapter_heading", 3: "chapter_heading"}
    roles = {SourceRef(20, i): LineRole(role, 0.9, 0.05) for i, role in not_body.items()}
    blocks = reflow([page(20, rows)], roles)
    assert [type(b) for b in blocks] == [Paragraph, Heading, Paragraph]
    assert blocks[0].text == "einde van een zin."
    assert blocks[1].text == "CHAPTER V."
    assert blocks[2].text == "Begin van het hoofdstuk dat doorloopt." and blocks[2].opening


def test_tidy_removes_space_before_punctuation_only():
    assert tidy("Sussex , and ; then !") == "Sussex, and; then!"
    assert tidy("a — b") == "a — b"
