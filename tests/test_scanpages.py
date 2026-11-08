from roboscriptorium import scanpages
from roboscriptorium.pdf import Line, PageText

WORDS = "de het een dat zij hij was niet maar ook nog wel toen".split()


def _page(number: int, seed: int, folio: int | None = None, short: bool = False) -> PageText:
    """A page of running text unlike any other seed's, its printed number at the foot."""
    n = 2 if short else 30
    lines = [
        Line(" ".join(WORDS[(seed * 7 + k * 3 + j) % len(WORDS)] + str(seed) for j in range(9)),
             40, 50 + 15 * k, 300, 60 + 15 * k)
        for k in range(n)
    ]  # fmt: skip
    if folio is not None:
        lines.append(Line(str(folio), 170, 560, 180, 570))
    return PageText(number, 340, 580, lines)


def test_a_page_held_twice_is_found_and_each_page_once_is_not():
    pages = [_page(n, n, n - 4) for n in range(10, 20)]
    # PDF 16 and 17 hold PDF 14 and 15 again; the printed numbers past them run on.
    pages[6] = _page(16, 14, 10)
    pages[7] = _page(17, 15, 11)
    assert scanpages.repeats(pages) == {16: 14, 17: 15}
    assert scanpages.repeats([_page(n, n, n - 4) for n in range(10, 30)]) == {}


def test_short_pages_alike_are_no_repeat():
    # Part title pages, or blank ones with a speck, look alike by design.
    pages = [_page(n, 1, short=True) for n in range(10, 14)]
    assert scanpages.repeats(pages) == {}


def test_pages_missing_where_the_printed_numbers_jump_and_hold():
    # PDF 10–15 print 6–11, PDF 16–21 print 14–19: printed 12 and 13 are not in the scan.
    pages = [_page(n, n, n - 4) for n in range(10, 16)]
    pages += [_page(n, n, n - 2) for n in range(16, 22)]
    assert scanpages.gaps(pages) == [scanpages.Gap(16, 12, 13)]
    summary = scanpages.summary({}, scanpages.gaps(pages))
    assert summary == "scan: printed 12–13 not in the scan (before PDF 16)"


def test_one_misread_number_or_an_unnumbered_page_is_no_gap():
    pages = [_page(n, n, n - 4) for n in range(10, 22)]
    pages[5] = _page(15, 15, 19)  # "19" read for 11
    pages[7] = _page(17, 17)  # a chapter's first page, no number
    assert scanpages.gaps(pages) == []
    # Three numbers in a row misread ("912"–"914" for 512–514), then the run goes on.
    pages = [_page(n, n, n - 4) for n in range(10, 30)]
    for jump in (400, 2):
        pages[8:11] = [_page(n, n, n - 4 + jump) for n in range(18, 21)]
        assert scanpages.gaps(pages) == []
    assert scanpages.summary({}, []) == ""


def test_a_page_the_readers_disagree_on_line_after_line_is_too_poor():
    pages = [_page(n, n) for n in range(10, 14)] + [_page(14, 14, short=True)]
    # 30 lines a page: PDF 11 holds 60 suspects (2.0 a line), PDF 12 holds 44 (1.47),
    # the short PDF 14 holds 6 of its 2 lines and is too short to tell.
    suspects = [11] * 60 + [12] * 44 + [10] * 3 + [14] * 6
    assert scanpages.poor(pages, suspects) == {11: 2.0}
    assert scanpages.summary({}, [], {11: 2.0}) == (
        "scan: PDF 11 (2.0 a line) too poor to read, out of the bench's score"
    )
