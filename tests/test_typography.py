from roboscriptorium.ir import Paragraph
from roboscriptorium.scanstyle import _decide
from roboscriptorium.typography import (
    DashStyle,
    EllipsisStyle,
    apply,
    ellipsised,
    guess_ellipsis,
    styled,
)

EN_THIN = DashStyle("–", "thin")
EM_GLUED = DashStyle("—", "none")
EN_WORD = DashStyle("–", "word")


def test_what_isnt_a_dash_between_words_stays():
    for text in ("de jaren 1914–1918", "een wc-bril en Mens-erger-je-niet", "pagina 12-14"):
        assert styled(text, EN_WORD)[0] == text


def test_a_number_range_or_a_minus_sign_stays_as_the_layer_reads_it():
    for text in (
        "de jaren 1914–1918",
        "de jaren 1914 – 1918",
        "de jaren 1914 — 1918",
        "het vroor –5 graden",
        "in 1914– en daarna",
        "bladzijde 3 - 4",
    ):
        for style in (EN_WORD, EN_THIN, EM_GLUED):
            assert styled(text, style)[0] == text


def test_a_dash_between_a_word_and_a_number_takes_the_books_style():
    assert styled("zei hij – 3 keer", EN_WORD)[0] == "zei hij\u00a0– 3 keer"
    assert styled("zei hij —  3 keer", EN_WORD)[0] == "zei hij\u00a0– 3 keer"
    assert styled("pagina 12 – dat", EM_GLUED)[0] == "pagina 12—dat"
    assert styled("pagina 12 – dat", EN_THIN)[0] == "pagina 12\u202f–\u2009dat"
    text, where = styled("zei hij – 3 keer", EM_GLUED)
    assert text == "zei hij—3 keer"
    assert len(where) == len("zei hij – 3 keer") and where[-1] == len(text) - 1


def test_every_dash_takes_the_books_style():
    for layer in ("irriteert—een", "irriteert – een", "irriteert— een", "irriteert -- een"):
        assert styled(layer, EN_THIN)[0] == "irriteert – een"
        assert styled(layer, EM_GLUED)[0] == "irriteert—een"
        assert styled(layer, EN_WORD)[0] == "irriteert – een"


def test_a_dash_by_a_quote_or_the_paragraphs_edge_takes_only_its_open_side():
    assert styled("‘Ik zei toch —’", EN_WORD)[0] == "‘Ik zei toch –’"
    assert styled("— Nee, zei ze.", EN_WORD)[0] == "– Nee, zei ze."
    assert styled("en dan —", EN_WORD)[0] == "en dan –"


def test_italic_marks_follow_their_words_when_words_split_or_join():
    p = Paragraph("hij las Ulysses—een boek", italic=(2,))
    (out,) = apply([p], EN_WORD)
    assert out.text == "hij las Ulysses – een boek"
    # The layer's word was italic as a whole; its halves stay so, the dash doesn't.
    assert [out.text.split()[k] for k in out.italic] == ["Ulysses", "een"]
    q = Paragraph("hij las Ulysses — een boek", italic=(4,))
    (out,) = apply([q], EM_GLUED)
    assert out.text == "hij las Ulysses—een boek"
    assert out.italic == (2,)
    assert p.text == "hij las Ulysses—een boek"


def test_the_guess_reads_kind_and_spacing_against_the_books_word_gap():
    def found(length, gap, word_gap):
        return [{"length": length, "left": gap, "right": gap, "word_gaps": [word_gap]}] * 5

    assert _decide(found(1.3, 0.45, 0.8)).style == EN_THIN
    assert _decide(found(1.2, 0.8, 0.8)).style == EN_WORD
    assert _decide(found(2.2, 0.05, 0.6)).style == EM_GLUED
    assert _decide(found(1.2, 0.8, 0.8)[:2]) is None


SPACED = EllipsisStyle(". . .", True)
GLYPH = EllipsisStyle("…", False)


def test_what_isnt_an_ellipsis_after_a_word_keeps_its_spacing():
    # Four dots, two dots and numbers aren't ellipses; one opening a quotation or a
    # paragraph takes no space before it.
    for text in ("So.... Next", "So . . . . Next", "a .. b", "versie 1.2.3", "www.x.nl"):
        assert ellipsised(text, SPACED)[0] == text
    assert ellipsised("‘...en dan", SPACED)[0] == "‘. . .en dan"
    assert ellipsised("... en dan", GLYPH)[0] == "… en dan"


def test_every_ellipsis_takes_the_books_style():
    for layer in ("people... The", "people . . . The", "people.. . The", "people … The"):
        assert ellipsised(layer, SPACED)[0] == "people . . . The"
        assert ellipsised(layer, GLYPH)[0] == "people… The"
    assert ellipsised("here.. .’ Artyom", SPACED)[0] == "here . . .’ Artyom"


def test_an_italic_word_before_an_ellipsis_stays_italic_and_the_dots_dont():
    p = Paragraph("hij las Ulysses... toen", italic=(2,))
    (out,) = apply([p], None, SPACED)
    assert [out.text.split()[k] for k in out.italic] == ["Ulysses"]


def test_the_ellipsis_guess_trusts_the_reads_that_kept_their_gaps():
    # A spaced book's layer merges dots and drops the gap before them on many lines.
    spaced = ["they were people . . . The"] * 6 + ["they were people... The"] * 9
    assert guess_ellipsis(spaced) == SPACED
    # A tight book: an odd spaced read is noise.
    tight = ["en toen... ging"] * 20 + ["en toen . . . ging"]
    assert guess_ellipsis(tight) == EllipsisStyle("...", False)
    assert guess_ellipsis(["en toen… ging"] * 12) == GLYPH
    assert guess_ellipsis(["en toen… ging"] * 3) is None
    # An ellipsis opening a line says nothing about the space before one.
    assert guess_ellipsis(["... en toen"] * 20) is None


def test_four_spaced_dots_survive_reflow_in_a_spaced_dots_book():
    from roboscriptorium import reflow
    from roboscriptorium.pdf import Line, PageText
    from roboscriptorium.typography import apply

    page = PageText(
        3, 300, 500, [Line("Hij wachtte . . . . Toen kwam ze . . . en zweeg.", 20, 50, 280, 60)]
    )
    blocks = apply(reflow.reflow([page]), None, SPACED)
    assert blocks[0].text == "Hij wachtte . . . . Toen kwam ze . . . en zweeg."


def test_an_unspaced_dash_keeps_an_italic_word_from_swallowing_its_neighbour():
    from roboscriptorium import epub

    para = Paragraph("Hij las Ulysses — een boek, en sliep.", italic=(2,))
    (styled,) = apply([para], EM_GLUED)
    assert styled.text == "Hij las Ulysses—een boek, en sliep."
    assert styled.italic == (2,) and styled.italic_parts == ((2, 0, 7),)
    assert "<i>Ulysses</i>—een" in epub._inline(
        styled.text, set(styled.italic), {k: (a, b) for k, a, b in styled.italic_parts}
    )
    # Whole italic words keep one run across punctuation.
    assert (
        epub._inline("Ze zei: ‘wat nu, vriend?’", {2, 3, 4}) == "Ze zei: ‘<i>wat nu, vriend</i>?’"
    )


def test_after_a_question_mark_an_ellipsis_keeps_the_layers_space():
    assert ellipsised("Waar? … Ik zocht", GLYPH)[0] == "Waar? … Ik zocht"
    assert ellipsised("Waar?… Ik zocht", GLYPH)[0] == "Waar?… Ik zocht"
    # After a word the book's style still decides.
    assert ellipsised("Waar … Ik zocht", GLYPH)[0] == "Waar… Ik zocht"


def _scan(tmp_path, printed: str, layer: str, font: str = "tiro"):
    """A one-page scan of `printed` lines (an image, as a scan is) under an invisible text
    layer reading `layer` on the same lines, both in `font`."""
    import pymupdf

    src = pymupdf.open()
    page = src.new_page(width=400, height=60 + 20 * 30)
    for k, line in enumerate(printed.splitlines()):
        page.insert_text((20, 40 + 20 * k), line, fontsize=14, fontname=font)
    png = page.get_pixmap(dpi=300).tobytes("png")
    out = pymupdf.open()
    scan = out.new_page(width=page.rect.width, height=page.rect.height)
    scan.insert_image(scan.rect, stream=png)
    for k, line in enumerate(layer.splitlines()):
        scan.insert_text((20, 40 + 20 * k), line, fontsize=14, fontname=font, render_mode=3)
    path = tmp_path / "scan.pdf"
    out.save(path)
    return path


def test_an_image_only_scans_dashes_are_measured_through_its_first_reading(tmp_path):
    import pymupdf

    from roboscriptorium.pdf import PageText
    from roboscriptorium.scanstyle import guess

    src = pymupdf.open()
    page = src.new_page(width=400, height=400)
    words = []
    for k in range(8):
        y = 40 + 24 * k
        x = 20.0
        for i, text in enumerate(["the", "people", "said", "–", "and", "then", "she"]):
            if text == "–":
                # An en dash about a letter long, at mid x-height, a word space either side.
                page.draw_rect(pymupdf.Rect(x, y - 4.6, x + 8, y - 3.6), color=None, fill=(0, 0, 0))
                box = (x, y - 4.6, x + 8, y - 3.6)  # a first reading's box hugs the stroke
                x += 8 + 4
            else:
                width = pymupdf.get_text_length(text, fontname="helv", fontsize=14)
                page.insert_text((x, y), text, fontsize=14, fontname="helv")
                box = (x, y - 10.5, x + width, y + 3)
                x += width + 4
            words.append((*box, text, 0, k, i))
    png = page.get_pixmap(dpi=300).tobytes("png")
    out = pymupdf.open()
    scan = out.new_page(width=400, height=400)
    scan.insert_image(scan.rect, stream=png)
    path = tmp_path / "image-only.pdf"
    out.save(path)
    first = PageText(1, 400, 400, [], words=tuple(words))
    found = guess(path, [1], tmp_path / "typography.json", [first])
    assert found is not None and found.style.dash == "–" and found.style.spacing != "none"


def test_the_scan_shows_the_space_the_layer_drops_before_spaced_dots(tmp_path):
    from roboscriptorium.scanstyle import measure_ellipses

    lines = ["the other people said Kate . . . and then", "she was there again . . . quite"]
    layer = ["the other people said Kate... and then", "she was there again... quite"]
    pdf = _scan(tmp_path, "\n".join(lines * 3), "\n".join(layer * 3))
    found = measure_ellipses(pdf, [1], tmp_path / "ellipsis.json")
    assert found is not None and found.ellipses == 6
    assert found.spaced and found.space_before
    # Cached: read back without the scan.
    pdf.unlink()
    assert measure_ellipses(pdf, [1], tmp_path / "ellipsis.json") == found


def test_the_scan_shows_tight_dots_glued_to_their_word(tmp_path):
    from roboscriptorium.scanstyle import measure_ellipses

    lines = ["the other people said Kate... and then", "she was there again... quite"]
    pdf = _scan(tmp_path, "\n".join(lines * 3), "\n".join(lines * 3))
    found = measure_ellipses(pdf, [1], tmp_path / "ellipsis.json")
    assert found is not None
    assert not found.spaced and not found.space_before


def test_the_scan_sets_the_gaps_and_the_layer_the_glyph_or_dots():
    from roboscriptorium.scanstyle import EllipsisMeasure, scanned_style

    spaced = EllipsisMeasure(60, 0.84, 0.93, 0.95)
    tight = EllipsisMeasure(60, 0.21, 0.35, 0.75)
    assert scanned_style(EllipsisStyle("...", False), spaced) == SPACED
    assert scanned_style(GLYPH, tight) == GLYPH
    assert scanned_style(EllipsisStyle(". . .", True), tight) == EllipsisStyle("...", False)
    assert scanned_style(None, tight) == EllipsisStyle("...", False)
    # Too few on the scan to tell: the layer's reading stands.
    assert scanned_style(GLYPH, None) == GLYPH


def test_a_scanned_books_ellipsis_style_comes_from_the_scan(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from roboscriptorium import pipeline
    from roboscriptorium.pdf import Line, PageText

    lines = ["the other people said Kate . . . and then", "she was there again . . . quite"]
    layer = ["the other people said Kate... and then", "she was there again... quite"] * 6
    pdf = _scan(tmp_path, "\n".join(lines * 3), "\n".join(layer[:6]))
    monkeypatch.setattr(pipeline.ocrcheck, "scanned", lambda source: True)
    book = SimpleNamespace(source=pdf, stages=tmp_path, ellipsis=None, ellipsis_space=None)
    body = [PageText(1, 400, 660, [Line(t, 20, 20, 380, 35) for t in layer])]
    # The layer alone reads tight dots glued to their word; the scan shows the gaps.
    assert guess_ellipsis(layer) == EllipsisStyle("...", False)
    assert pipeline.ellipsis_style(book, body) == SPACED
    # book.toml settles it.
    book.ellipsis, book.ellipsis_space = "…", False
    assert pipeline.ellipsis_style(book, body) == GLYPH


def test_a_printed_blank_takes_the_books_setting_however_many_underscores_were_read():
    p = Paragraph("naar het __plein, dan het _plein en de ____straat in", italic=(1,))
    tight = EllipsisStyle("...", False)
    (out,) = apply([p], None, tight, "...")
    assert out.text == "naar het ...plein, dan het ...plein en de ...straat in"
    assert [out.text.split()[k] for k in out.italic] == ["het"]


def test_without_a_setting_a_blank_stays_as_read():
    p = Paragraph("naar het __plein")
    assert apply([p], None, EllipsisStyle("...", False))[0].text == "naar het __plein"
