import io

from roboscriptorium.progress import Progress, duration


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_quiet_until_a_stage_has_run_a_while_then_says_how_far_and_how_long():
    clock, out = Clock(), io.StringIO()
    p = Progress("readings, glm-ocr", 100, "lines", every=180, clock=clock, out=out)
    clock.now = 60
    p.add(10)
    assert out.getvalue() == ""
    clock.now = 200
    p.add(10)
    assert out.getvalue() == "readings, glm-ocr: 20 of 100 lines, about 13 min left\n"
    clock.now = 250
    p.add(10)
    assert out.getvalue().count("\n") == 1


def test_the_last_item_prints_nothing():
    clock, out = Clock(), io.StringIO()
    p = Progress("judges", 2, "pages", every=0, clock=clock, out=out)
    clock.now = 10
    p.add(2)
    assert out.getvalue() == ""


def test_duration():
    assert duration(20) == "under a minute"
    assert duration(12 * 60) == "12 min"
    assert duration(2 * 3600 + 5 * 60) == "2 h 05 min"
