from roboscriptorium.pdf import Line, PageText
from roboscriptorium.roles import Repeats


def _page(number: int, top: str) -> PageText:
    lines = [Line(top, 100, 50, 300, 60)] + [
        Line("body text " * 5, 50, 80 + 15 * i, 350, 92 + 15 * i) for i in range(10)
    ]
    return PageText(number, 400, 600, lines)


def test_running_heads_repeat_but_chapter_numbers_differ():
    pages = [_page(1, "CHAPTER I.")] + [
        _page(n, f"SENSE AND SENSIBILITY. {n}" if n % 3 else f"CHAPTER {'I' * (n // 3 + 1)}.")
        for n in range(2, 20)
    ]
    repeats = Repeats(pages)
    assert repeats.other_pages("CHAPTER II.", 3) == 0
    assert repeats.other_pages("SENSE AND SENSIBILTY. 4", 4) >= 5  # OCR noise still matches
