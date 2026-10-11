"""Footnotes found at a page's foot, collected into notes, linked to their marks."""

from roboscriptorium import footnotes
from roboscriptorium.ir import Paragraph, SourceRef
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.roles import LineRole
from roboscriptorium.typestyle import Style

BODY = Style(1.0, 1.0, 1.0, False)
SMALL = Style(0.7, 0.8, 1.0, False)


def _page(rows: list[tuple[str, Style | None]], number: int = 5):
    lines = [Line(t, 10, 20 + 12 * i, 280, 30 + 12 * i) for i, (t, _) in enumerate(rows)]
    styles = {SourceRef(number, i): s for i, (_, s) in enumerate(rows) if s is not None}
    return PageText(number, 300, 500, lines), styles


def test_small_lines_at_the_foot_without_a_mark_are_no_note():
    # A caption or a smaller closing line, set small but opening on no mark.
    page, styles = _page([("Tekst van het boek.", BODY), ("Een kleiner gezet slot", SMALL)])
    assert footnotes.lines([page], {}, styles) == set()
    # A page all in small type has no running text above a note.
    page, styles = _page([("*Alleen klein.", SMALL), ("nog klein", SMALL)])
    assert footnotes.lines([page], {}, styles) == set()
    # Small lines with a mark above the body's last line aren't at the foot.
    page, styles = _page([("*Klein boven", SMALL), ("Tekst van het boek.", BODY)])
    assert footnotes.lines([page], {}, styles) == set()


def test_marked_small_lines_at_the_foot_are_notes_and_the_page_number_is_not():
    rows = [("Tekst tot de berg*.", BODY), ("*_Een berg bij de", SMALL), ("stad. (vert)", SMALL)]
    rows += [("2", SMALL), ("87", Style(0.8, 0.9, 1.0, False))]
    page, styles = _page(rows)
    roles = {SourceRef(5, 4): LineRole("page_number", 0.9, 0.01)}
    # The lone "2" between two notes is a note's own mark line here; the folio is dropped.
    assert footnotes.lines([page], roles, styles) == {SourceRef(5, i) for i in (1, 2, 3)}


def test_notes_collect_their_lines_and_link_to_their_marks():
    rows = [("Tekst tot de berg*. En ver-", BODY), ("der tot de trein**.", BODY)]
    rows += [("*_Een berg bij de", SMALL), ("stad. (vert)", SMALL), ("** Een trein.", SMALL)]
    page, styles = _page(rows)
    found = footnotes.lines([page], {}, styles)
    notes = footnotes.collect([page], found)
    assert [(n.mark, n.paragraph.text) for n in notes] == [
        ("*", "Een berg bij de stad. (vert)"),
        ("**", "Een trein."),
    ]
    text = Paragraph("Tekst tot de berg*. En verder tot de trein**.", [SourceRef(5, 0)])
    other = Paragraph("Op een andere pagina*.", [SourceRef(6, 0)])
    blocks = footnotes.link([text, other], notes)
    assert blocks[0].notes == [0, 1] and blocks[1].notes == []
    assert all(n.linked for n in notes)
    assert text.notes == []  # the input is left alone


def test_a_note_whose_mark_the_layer_misread_goes_after_its_pages_last_paragraph():
    page, styles = _page([("Tekst tot de berg”.", BODY), ("*_Een berg.", SMALL)])
    notes = footnotes.collect([page], footnotes.lines([page], {}, styles))
    first = Paragraph("Tekst tot de berg”.", [SourceRef(5, 0)])
    blocks = footnotes.link([first], notes)
    assert blocks[0].notes == [0] and not notes[0].linked


def test_a_number_standing_on_its_own_is_no_mark():
    assert footnotes._mark_at("in 1950 omgedoopt", "1") is None
    assert footnotes._mark_at("de berg1 en", "1") is not None
    assert footnotes._mark_at("de berg.*", "*") is not None


def test_small_type_read_from_a_picture_is_no_note():
    rows = [("Tekst van het boek gaat door.", BODY), ("5 Savane ee ing vespteckam tic", SMALL)]
    page, styles = _page(rows)
    words = {"tekst", "van", "het", "boek", "gaat", "door", "een", "berg", "bij", "de", "stad"}
    known = words.__contains__
    assert footnotes.lines([page], {}, styles, known) == set()
    page, styles = _page([("Tekst van het boek.", BODY), ("*_Een berg bij de stad.", SMALL)])
    assert footnotes.lines([page], {}, styles, known) == {SourceRef(5, 1)}


def test_heavy_small_marks_from_a_picture_are_no_note():
    heavy = Style(0.4, 2.2, 0.5, False)
    page, styles = _page([("Tekst van het boek.", BODY), ("8 : 5 hd Eed Ld", heavy)])
    assert footnotes.lines([page], {}, styles) == set()
