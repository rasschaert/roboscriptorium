from roboscriptorium.golden import notes
from roboscriptorium.ir import Document, Paragraph, SourceRef
from roboscriptorium.pdf import Line, PageText

NOTE = "* Een in 1934 in gebruik genomen dieseltrein die de afstand aflegde. (vert.)"


def _page() -> PageText:
    texts = [
        "Nat en hoestend stappen wij in de railbus* die naar",
        "Wenen vertrekt. (vert.)",
        "* Een in 1934 in gebruik genomen dieseltrein die",
        "de afstand aflegde.",
        "(vert.)",
    ]
    return PageText(
        5, 300, 400, [Line(t, 10, 10 + 12 * i, 200, 20 + 12 * i) for i, t in enumerate(texts)]
    )


def test_only_the_lines_that_print_a_note_are_its_lines():
    found = notes.note_lines([_page()], [NOTE])
    # A short body line that happens to share a note's words isn't one.
    assert found == {SourceRef(5, 2), SourceRef(5, 3), SourceRef(5, 4)}


def test_the_scored_copy_drops_note_words_and_leaves_the_document_alone():
    page = _page()
    text = " ".join(ln.text for ln in page.lines)
    italic = (7, 20)  # "railbus*" and "dieseltrein"
    para = Paragraph(text, [SourceRef(5, i) for i in range(5)], italic=italic)
    doc = Document("T", "A", "nl", [para])
    scored = notes.without(doc, notes.note_lines([page], [NOTE]), {5: page})
    assert (
        scored.paragraphs[0].text
        == "Nat en hoestend stappen wij in de railbus* die naar Wenen vertrekt. (vert.)"
    )
    assert scored.paragraphs[0].italic == (7,)
    assert doc.paragraphs[0].text == text


def test_a_line_typed_in_above_a_note_leaves_the_right_words_out():
    # The document's sources are positions before answers; a typed line (inserted at
    # the top of the corrected copy) shifts every line below it there, not here.
    page = _page()
    typed = Paragraph("Een getypte regel.", [SourceRef(5, 0, typed=True)])
    para = Paragraph(" ".join(ln.text for ln in page.lines), [SourceRef(5, i) for i in range(5)])
    doc = Document("T", "A", "nl", [typed, para])
    out = notes.scored(doc, [page], [NOTE])
    assert out.paragraphs[0].text == "Een getypte regel."
    assert out.paragraphs[1].text.endswith("Wenen vertrekt. (vert.)")
