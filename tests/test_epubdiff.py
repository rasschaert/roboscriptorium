"""What a build changed against the book's previous build."""

from roboscriptorium import epubdiff
from roboscriptorium.epub import write_epub
from roboscriptorium.ir import Document, Heading, Paragraph


def _epub(tmp_path, name: str, blocks: list) -> list[tuple[str, str]]:
    out = tmp_path / f"{name}.epub"
    write_epub(Document("T", "A", "nl", blocks), out)
    return epubdiff.blocks(out)


def test_the_same_text_with_other_markup_is_no_change(tmp_path):
    old = _epub(tmp_path, "a", [Heading("1"), Paragraph("Een <zin> & meer.", opening=True)])
    new = _epub(tmp_path, "b", [Heading("1"), Paragraph("Een <zin> & meer.", italic=(0,))])
    assert old == [("h", "1"), ("p", "Een <zin> & meer.")]
    changes = epubdiff.compare(old, new)
    assert epubdiff.summary(changes) == "since the last build: no text changed"


def test_a_changed_heading_a_changed_paragraph_and_an_added_one_are_counted(tmp_path):
    old = _epub(tmp_path, "a", [Heading("Io"), Paragraph("Een."), Paragraph("Twee.")])
    new = _epub(tmp_path, "b", [Heading("10"), Paragraph("Een!"), Paragraph("Twee."),
                                Paragraph("Drie.")])  # fmt: skip
    changes = epubdiff.compare(old, new)
    assert epubdiff.summary(changes) == (
        "since the last build: headings 1 changed; paragraphs 1 changed, 1 added"
    )
    assert ("h", "Io", "10") in changes.places and ("p", "", "Drie.") in changes.places
    assert "- Io\n+ 10" in epubdiff.report(changes)
