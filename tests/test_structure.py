"""What a reader would notice in a built book's structure."""

from roboscriptorium import structure
from roboscriptorium.ir import Document, Heading, Paragraph, SourceRef

TEXT = " ".join(["woord"] * 30)


def _doc(*items: str) -> Document:
    """Headings for the strings starting with "#", else paragraphs; each on its own page."""
    blocks = []
    for n, item in enumerate(items, 1):
        ref = [SourceRef(n, 0)]
        blocks.append(
            Heading(item[1:], ref, [item[1:]]) if item[0] == "#" else Paragraph(item, ref)
        )
    return Document("T", "A", "nl", blocks)


def _kinds(doc: Document) -> list[tuple[str, str]]:
    return [(f.kind, f.text) for f in structure.findings(doc)]


def test_a_part_title_a_restart_at_one_or_a_part_over_its_chapter_is_no_finding():
    doc = _doc("#Boek een", "#1", TEXT, "#2", TEXT, "#3", TEXT,
               "#Boek 2", "#1", TEXT, "#2", TEXT, "#3", TEXT)  # fmt: skip
    assert _kinds(doc) == []
    titled = _doc("#Proloog", TEXT, "#Aan de Dender", TEXT, "#Een ramp", TEXT)
    assert _kinds(titled) == []
    motto = Document("T", "A", "nl", [
        Paragraph("Voor mijn ouders", dedication=True), Paragraph("Albert Camus", epigraph=True),
        Heading("1"), Paragraph(TEXT),
    ])  # fmt: skip
    assert _kinds(motto) == []


def test_a_number_out_of_its_run_a_stray_title_and_a_split_line_are_findings():
    doc = _doc("Voor mijn ouders", "#Bruni en Thomas Eggers", TEXT, "#1", TEXT, "#2", TEXT,
               "#3", TEXT, "#EO", TEXT, "#5", TEXT, "#6", TEXT, "#8", TEXT)  # fmt: skip
    assert _kinds(doc) == [
        ("short-section", "Voor mijn ouders"),
        ("title-among-numbers", "EO"),
        ("number-out-of-run", "8"),
    ]
    assert structure.summary(structure.findings(doc)).startswith("structure: 1 × a section")
    assert structure.summary([]) == "structure: nothing out of place"


def test_a_finding_is_asked_at_its_line_on_its_own_or_beside_a_question_there():
    from roboscriptorium import flags
    from roboscriptorium.pdf import Line, PageText

    page = PageText(9, 300, 500, [Line("Voor mijn ouders", 100, 40, 200, 52)])
    other = PageText(12, 300, 500, [Line("EO", 140, 40, 160, 52)])
    found = [
        structure.Finding("short-section", "Voor mijn ouders", SourceRef(9, 0)),
        structure.Finding("title-among-numbers", "EO", SourceRef(12, 0)),
    ]
    there = flags.Flag("k", 12, 0, 0, "EO", "heading", ["heading"])
    out = flags.structural([page, other], {}, found, [there])
    assert [(f.page, f.text, f.reasons) for f in out] == [
        (9, "Voor mijn ouders", ["short-section"]),
        (12, "EO", ["heading", "title-among-numbers"]),
    ]
    assert all(r in flags.REASONS for f in out for r in f.reasons)


def test_labelled_chapter_numbers_out_of_their_run_are_found():
    doc = _doc(*[x for n in (2, 4, 5, 6, 9, 10) for x in (f"#HOOFDSTUK {n}", TEXT)])
    assert [(k, t) for k, t in _kinds(doc)] == [
        ("number-out-of-run", "HOOFDSTUK 4"),
        ("number-out-of-run", "HOOFDSTUK 9"),
    ]
