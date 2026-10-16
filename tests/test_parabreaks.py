import pymupdf

from roboscriptorium import parabreaks
from roboscriptorium.clients.decide import Answer
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import Line, PageText
from roboscriptorium.roles import DecisionCache, LineRole


def test_a_line_can_start_a_paragraph_after_a_sentences_end_or_off_lower_case():
    assert parabreaks.can_start("en dat was dat.", "en toen")
    assert parabreaks.can_start("‘Kom je?’", "‘Ja.’")
    assert parabreaks.can_start("en toen ging hij", "Banks keek")
    assert parabreaks.can_start("", "en toen")
    # Lower case after a sentence still going on carries it on.
    assert not parabreaks.can_start("en toen ging hij", "naar huis")
    assert not parabreaks.can_start("de man met de", "hoed, die")


class Judge:
    model = "clef:27b"

    def __init__(self, answers: dict[str, tuple[str, float]]):
        self.answers = answers
        self.asked: list[str] = []

    def decide(self, state, questions, image_png=None):
        line = state["line in question"]
        self.asked.append(line)
        value, sure = self.answers[line]
        return {"start": Answer("choice", value, sure, {})}


def _scan(tmp_path, texts):
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=600)
    for i, t in enumerate(texts):
        page.insert_text((40, 60 + 18 * i), t, fontsize=11)
    doc.save(tmp_path / "s.pdf")
    lines = [Line(t, 40, 50 + 18 * i, 360, 62 + 18 * i) for i, t in enumerate(texts)]
    return tmp_path / "s.pdf", [PageText(1, 400, 600, lines)]


def test_the_judges_sure_answers_set_paragraph_starts_and_the_rest_stay(tmp_path):
    texts = [
        "Hij keek op. Het was al laat.",
        "‘Kom je nog?’ riep ze van beneden.",
        "Hij zei niets en ging weer verder met",
        "zijn brief. Toen stond hij op.",
        "Buiten regende het.",
        "Het was koud.",
    ]
    pdf, pages = _scan(tmp_path, texts)
    pages[0].lines[5] = Line(texts[5], 40, 140, 360, 152, starts_paragraph=False)
    judge = Judge(
        {
            texts[0]: ("starts", 0.9),
            texts[1]: ("starts", 0.95),
            texts[2]: ("continues", 0.8),
            texts[4]: ("starts", 0.5),
        }
    )
    cache = DecisionCache(tmp_path / "decisions.jsonl")
    (page,) = parabreaks.judged(pdf, pages, None, judge, cache)
    starts = [ln.starts_paragraph for ln in page.lines]
    # Sure answers set the start; "zijn brief." can't start one; an unsure answer and an
    # answered line are left as they were.
    assert starts == [True, True, False, False, None, False]
    assert texts[3] not in judge.asked and texts[5] not in judge.asked
    assert pages[0].lines[1].starts_paragraph is None
    # Asked again, the answers come from the cache.
    again = Judge({})
    parabreaks.judged(pdf, pages, None, again, cache)
    assert again.asked == []


def test_a_line_that_isnt_body_isnt_asked(tmp_path):
    pdf, pages = _scan(tmp_path, ["HOOFDSTUK EEN", "Het regende."])
    roles = {SourceRef(1, 0): LineRole("chapter_heading", 0.9, 0.05)}
    judge = Judge({"Het regende.": ("starts", 0.9)})
    (page,) = parabreaks.judged(pdf, pages, roles, judge, DecisionCache(tmp_path / "d.jsonl"))
    assert judge.asked == ["Het regende."]
    assert page.lines[0].starts_paragraph is None
