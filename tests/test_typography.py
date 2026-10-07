from roboscriptorium.ir import Paragraph
from roboscriptorium.typography import DashStyle, _decide, apply, styled

EN_THIN = DashStyle("–", "thin")
EM_GLUED = DashStyle("—", "none")
EN_WORD = DashStyle("–", "word")


def test_what_isnt_a_dash_between_words_stays():
    for text in ("de jaren 1914–1918", "een wc-bril en Mens-erger-je-niet", "pagina 12-14"):
        assert styled(text, EN_WORD)[0] == text


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
