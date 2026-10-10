from roboscriptorium.ir import Paragraph
from roboscriptorium.typography import (
    DashStyle,
    EllipsisStyle,
    _decide,
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
