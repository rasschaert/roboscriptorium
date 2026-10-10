from roboscriptorium import disagreements, lexicon
from roboscriptorium.disagreements import Disagreement, Verdicts, _auto, _spans, garbled, patch
from roboscriptorium.golden.reference import Chapter
from roboscriptorium.ir import Document, Paragraph, SourceRef
from roboscriptorium.lexicon import Lexicon
from roboscriptorium.pdf import Line, PageText


def test_close_differences_merge_into_one():
    out = "the family had been long settled in Sussex".split()
    ref = "the family had long been settled in Sussex".split()
    assert len(_spans(out, ref)) == 1


def test_garbled_output_needs_no_review():
    vocab = {"nothing", "and", "their", "every", "thing", "kost", "de"}
    assert garbled("nQthiri£,\\and", vocab)
    assert garbled("tlfat", vocab)
    assert not garbled("every thing", vocab)
    # Symbols a printed page uses, in Dutch books too.
    assert not garbled("kost € 5, 50% * /", vocab)
    # An accent the word list lacks is a misreading.
    assert garbled("dé", vocab)


def test_differences_only_in_spacing_are_resolved_by_kind():
    vocab: set[str] = set()
    assert _auto("every thing:", "everything:", vocab) == "hyphen"
    assert _auto("now !", "now!", vocab) == "punctuation"


def _book(text: str) -> tuple[Document, list[PageText]]:
    page = PageText(9, 300, 500, [Line(text, 20, 20, 280, 35)])
    return Document("t", "a", "nl", [Paragraph(text, [SourceRef(9, 0)])]), [page]


def test_auto_resolution_uses_the_books_language(monkeypatch):
    lists = {"nld": {"hij", "had", "gelopen"}, "eng": {"he", "had"}}
    monkeypatch.setattr(lexicon.Lexicon, "load", lambda lang: Lexicon(lists[lang]))
    doc, pages = _book("Hij had gelopen")
    reference = [Chapter("1", ["Hij had geloopen"])]
    (found,) = disagreements.find(doc, reference, pages, language="nl")
    assert found.auto is None
    (found,) = disagreements.find(doc, reference, pages, language="en")
    assert found.auto == "ocr"


def test_dutch_low_quotes_are_folded_as_quotes(monkeypatch):
    monkeypatch.setattr(lexicon.Lexicon, "load", lambda lang: Lexicon({"ja"}))
    doc, pages = _book("„Ja”, zei")
    (found,) = disagreements.find(doc, [Chapter("1", ["“Ja”, zegt"])], pages, language="nl")
    assert found.got == "zei"


def test_patch_leaves_paragraphs_without_verdicts_as_they_were(tmp_path):
    reference = [Chapter("1", ["Wait . . . what now", "Then\u00a0. . . go"], [frozenset({4})])]
    patched, applied = patch(reference, Verdicts(tmp_path / "v.jsonl"))
    assert applied == 0
    assert patched[0].paragraphs == reference[0].paragraphs
    assert patched[0].italic[0] == frozenset({4})


def test_patch_maps_printed_words_through_spaced_dots(tmp_path):
    reference = [Chapter("1", ["Wait . . . what now", "Next."], [frozenset({4})])]
    verdicts = Verdicts(tmp_path / "v.jsonl")
    d = Disagreement("k", "what", "what", "Wait ...", "now Next.", 7, (1, 1))
    verdicts.record(d, "who", "edition")
    patched, applied = patch(reference, verdicts)
    assert applied == 1
    assert patched[0].paragraphs == ["Wait . . . who now", "Next."]
    assert patched[0].italic == [frozenset({4}), frozenset()]


def test_patch_puts_the_scan_reading_into_the_reference(tmp_path):
    reference = [Chapter("I", ["She was eager in everything: her sorrows.", "Next."])]
    verdicts = Verdicts(tmp_path / "v.jsonl")
    d = Disagreement(
        "k", "every thing:", "everything:", "She was eager in", "her sorrows.", 7, (1, 1)
    )
    verdicts.record(d, "every thing:", "edition")
    patched, applied = patch(reference, verdicts)
    assert applied == 1
    assert patched[0].paragraphs == ["She was eager in every thing: her sorrows.", "Next."]
    # Verdicts persist and reload.
    assert Verdicts(tmp_path / "v.jsonl").by_key["k"].truth == "every thing:"


def test_patch_keeps_italic_words(tmp_path):
    reference = [Chapter("I", ["She was eager in everything: her sorrows."], [frozenset({4, 6})])]
    verdicts = Verdicts(tmp_path / "v.jsonl")
    d = Disagreement(
        "k", "every thing:", "everything:", "She was eager in", "her sorrows.", 7, (1, 1)
    )
    verdicts.record(d, "every thing:", "edition")
    patched, _ = patch(reference, verdicts)
    assert patched[0].italic == [frozenset({4, 5, 7})]


def test_patch_keeps_the_printed_glyphs(tmp_path):
    reference = [Chapter("I", ["‘Wacht…’ zei ze. ‘Ik kom.’"])]
    verdicts = Verdicts(tmp_path / "v.jsonl")
    d = Disagreement("k", "kom.'", "kom.'", "'Wacht...' zei ze. 'Ik", "", 7, (1, 1))
    verdicts.record(d, "kwam.'", "edition")
    patched, applied = patch(reference, verdicts)
    assert applied == 1
    assert patched[0].paragraphs == ["‘Wacht…’ zei ze. ‘Ik kwam.'"]


def test_patch_applies_verdicts_within_each_others_context(tmp_path):
    reference = [Chapter("I", ["a b c d e f g h i j k l m n o"])]
    verdicts = Verdicts(tmp_path / "v.jsonl")
    verdicts.record(Disagreement("1", "E", "e", "a b c d", "f g h i", 7, (1, 1)), "E", "edition")
    verdicts.record(Disagreement("2", "G", "g", "c d e f", "h i j k", 7, (1, 1)), "G", "edition")
    patched, applied = patch(reference, verdicts)
    assert applied == 2
    assert patched[0].paragraphs == ["a b c d E f G h i j k l m n o"]


def _two_pages(first: str, second: str) -> tuple[Document, list[PageText]]:
    pages = [
        PageText(37, 300, 500, [Line(first, 20, 20, 280, 35)]),
        PageText(38, 300, 500, [Line(second, 20, 20, 280, 35)]),
    ]
    para = Paragraph(f"{first} {second}", [SourceRef(37, 0), SourceRef(38, 0)])
    return Document("t", "a", "nl", [para]), pages


def test_an_error_over_a_page_break_belongs_to_the_page_holding_most_of_it():
    # Mostly on the first page: it stays there.
    doc, pages = _two_pages("de man liep xq zw vk", "naar huis toe")
    (found,) = disagreements.find(
        doc, [Chapter("1", ["de man liep heel snel weg naar huis toe"])], pages
    )
    assert found.page == 37
    # A washed-out page read as scraps, its error starting on the page before.
    doc, pages = _two_pages("de man liep naar zq", "xq zw vk pt ab cd ef")
    ref = [Chapter("1", ["de man liep naar huis en sliep daar die hele lange nacht"])]
    (found,) = disagreements.find(doc, ref, pages)
    assert found.page == 38


def test_a_disagreement_at_a_slices_edge_keeps_its_whole_book_key(monkeypatch, tmp_path):
    monkeypatch.setattr(lexicon.Lexicon, "load", lambda lang: Lexicon(set()))
    whole = [
        Chapter("1", ["Het eerste hoofdstuk eindigt hier rustig."]),
        Chapter("2", ["Daarna kwam de storm over het land."]),
    ]
    doc, pages = _book("Daarna kwam de starm over het land.")
    (in_whole,) = [d for d in disagreements.find(doc, whole, pages, "nl") if d.want == "storm"]
    sliced, around = disagreements.slice_reference(whole, (2, 2))
    (in_slice,) = disagreements.find(doc, sliced, pages, "nl", around)
    assert in_slice.key == in_whole.key
    assert in_slice.before == "eindigt hier rustig. Daarna kwam de"
    # A verdict recorded on the whole book applies to the slice.
    verdicts = Verdicts(tmp_path / "v.jsonl")
    verdicts.record(in_whole, "starm", "edition")
    patched, applied = patch(sliced, verdicts, around)
    assert applied == 1 and patched[0].paragraphs == ["Daarna kwam de starm over het land."]
