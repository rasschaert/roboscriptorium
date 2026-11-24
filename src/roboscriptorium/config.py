"""Runtime settings, overridable through environment variables."""

import os
from dataclasses import dataclass


def _flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    if value.lower() in ("1", "true", "yes", "on"):
        return True
    if value.lower() in ("0", "false", "no", "off"):
        return False
    raise ValueError(f"{name}={value!r}: use 1 or 0")


@dataclass(frozen=True)
class Settings:
    ollama_url: str = "http://127.0.0.1:11434"
    role_model: str = "clef-flash:9b"
    # Reads OCR suspects from the sentence, not the image, asked through token
    # probabilities. Right alone on 81%, and an alarm on the judge: clef is wrong 2% where
    # it agrees, 35% where it doesn't (docs/design.md).
    check_model: str = "tokens:hf.co/Piotr1215/Winnow-12B-GGUF:Q4_K_M"
    # Judges the OCR check's suspects from the crop; better than role_model at that,
    # worse at line roles.
    judge_model: str = "clef:27b"
    # Second vision judges on the OCR check's suspects, comma-separated: decision models
    # on Ollama, or `llama:<name>` served by llama.cpp at llama_url (`clients/llama.py`,
    # imajev-4b); `<model>@wide` asks one on the suspect with its line around it;
    # `<model>@text` asks it the text judge's question (the sentence, no scan), and
    # `<model>@words` the same only where the versions' words differ; `render`
    # is no model: each version drawn in the book's typeface and laid over the
    # scan (`rendercheck.py`, with the fonts in `fonts`). Each
    # is a vote for the arbiter, "" for none. Asked only where the vision judge is less
    # sure than `alarm_below` (1.0: always). autotrust-jev 35B and d3 9B: the arbiter
    # trained with their votes leaves about a tenth fewer errors silent; with `render`
    # too it asks about an eighth fewer questions on tuning; autotrust-jev 9B asked the text
    # judge's question beside them, about 1% fewer questions and as many errors silent
    # (2026-11-15, docs/design.md); Shisa DE-1 asked the text question too, read through its
    # answer's token probabilities, with the arbiters trained on 26 books: 3% fewer errors
    # silent and 1% fewer questions on tuning, validation level (2026-11-23).
    alarm_model: str = (
        "autotrust-jev:35b-nvfp4,d3:9b,render,autotrust-jev:9b-nvfp4@text,"
        "tokens:hf.co/mradermacher/shisa-de-1-GGUF:Q8_0@text"
    )
    alarm_below: float = 1.0
    # More judges of a line-end hyphen the book and the word list leave undecided, asked
    # beside the judge, in Dutch books too (comma-separated; `hyphens.Compounds`).
    hyphen_judge: str = "autotrust-jev:35b-nvfp4,d3:9b,autotrust-jev:9b-nvfp4"
    # The decision on those breaks, learned from the golden books' spellings, the book's
    # own signs and each judge's chance (`hyphens.Learned`, `experiments/train_hyphens.py`):
    # on tuning 27 silent errors fixed and 14 made, all compound hyphens (2026-11-18,
    # docs/design.md). Empty, the judges' chances are averaged.
    hyphen_learned: str = "work/models/hyphens.pkl"
    # Doubts raised where small capitals may have been read in lower case though every
    # reading agrees ("ss", "usb-stick"; `ocrcheck.capitals_doubts`). About 1.7% more
    # questions for the small capitals no reader disputes (docs/design.md).
    lower_capitals: bool = True
    # A heading the line-role trees call at least this sure, by their own call, with
    # nothing else to ask on its lines (every place in it settled by the readers and
    # judges), isn't asked; 0 asks every heading. At 0.99 the trees were never wrong
    # about a heading on tuning (463 of 470; the other 7 misread numbers the OCR check
    # mends): 113 fewer questions on tuning, 4 on validation, no word moved, and
    # Nervous System's heading questions 13 → 4 (decisions.md, 2026-11-21 and 22).
    sure_heading: float = 0.99
    # Doubts raised where the scan shows a stress accent over a word every reading has
    # plain ("zíjn" read "zijn"; `accentmarks.py`), in a Dutch book with the judge
    # `render`. Decided by `offer_trust_model` (docs/decisions.md, 2026-11-18 and 11-19).
    accent_doubts: bool = True
    # Doubts raised where the scan shows three ticks at a double quote mark every reading
    # agrees on (a nested quotation's outer mark lost; `quotemarks.py`). Off until its
    # bench (docs/decisions.md, 2026-11-15).
    nested_quote_doubts: bool = False
    # Doubts raised where a comma, semicolon or colon is unlike the book's own (a speck
    # read as punctuation; `speckmarks.py`). Decided by `offer_trust_model` (docs/decisions.md,
    # 2026-11-18 and 11-19).
    speck_doubts: bool = True
    # The judges' crops and the render judge's window stop at the line above's
    # descenders (`readers.own_span`): set tight, a padded crop holds them, and judges
    # took them for marks (Andere levens' "dië").
    crop_descent: bool = False
    llama_url: str = "http://127.0.0.1:8092"
    # The font library the judge `render` draws with: a folder of .otf and .ttf files.
    fonts: str = "work/fonts"
    # A hosted build of judge_model that answers in its place (`openrouter:…`, used only
    # when the user asks), its answers cached under judge_model's name. "" for none.
    judge_via: str = ""
    # OCR model on Ollama for the OCR check's second reading of each line.
    ocr_model: str = "glm-ocr:bf16"
    # Vision model on Ollama, told the book's style: the OCR check's third reading of
    # each body line, and the reading of the lines quote questions sit on ("" for none).
    read_model: str = "qwen3.8:27b-nvfp4"
    # A hosted build of read_model that reads in its place (`openrouter:…`, used only
    # when the user asks): its readings are cached under read_model's name, each line
    # marked with the build that read it. "" reads with read_model itself.
    read_via: str = ""
    # ocr_model and read_model also read each body page whole (`pagereader.py`): two more
    # readers for the OCR check, which the arbiter must be trained with.
    page_readers: bool = False
    # Learned trust (`trust.py`) chooses the OCR check's fixes and questions instead of
    # the fixed rule, asking at most this many questions per page.
    ocr_trust: bool = True
    # The (page, line) pairs the OCR check's judges are asked anew on; elsewhere they answer
    # from the cache or not at all. Set by `trustdata` on a book labelled by review answers,
    # where only the answered lines become training rows; never from the environment.
    judge_lines: frozenset[tuple[int, int]] | None = None
    ocr_trust_model: str = "work/models/ocr-trust.pkl"
    # A second arbiter that decides only the suspects holding a version no reading has (an
    # offer from a measure on the scan: the accent and speck doubts); "" decides them with
    # `ocr_trust_model` like the rest.
    offer_trust_model: str = "work/models/ocr-trust-offers.pkl"
    ocr_questions_per_page: float = 1.0
    # Within that budget, a suspect whose likeliest version is right with at least this
    # chance (the trust model's calibrated sureness) is decided, not asked (1.0: every
    # one may be asked). 0.93 on the smooth calibration asks about as much as the user's
    # trade of questions for silent errors did (docs/design.md).
    ocr_ask_below: float = 0.93
    # Line roles from trees over layout, type and the role model's answer (`sorter.py`)
    # on top of the rules in `roles.py` (docs/design.md, "Line roles").
    sorter: bool = True
    sorter_model: str = "work/models/line-roles.pkl"
    # A second set of line-role trees; the judge, shown the page, settles the lines the
    # two sets call differently (`sorter.Referee`; `ROBO_SORTER_SECOND=` turns it off).
    sorter_second: str = "work/models/line-roles-second.pkl"
    # Italic words decided by trees over each word's slant and its neighbours'
    # (`italics.Trees`, trained on the golden pairs' words) instead of the cuts in
    # `italics._italic` (`ROBO_ITALIC_TREES=0`).
    italic_trees: bool = True
    italic_model: str = "work/models/italics.pkl"
    # A second set of italic trees and the vision judge that settles the words the two
    # disagree on (`italics.settle`); "" for either leaves the first set alone. The trees
    # trained on the grown slices, the first set's held out from Het geluid van bananen
    # (a book set mostly in italics): italic errors 1,223 → 986 on tuning, 195 → 170 on
    # validation, nothing else moved (the user's idea, 2026-11-14; docs/design.md).
    italic_second: str = "work/models/italics-second.pkl"
    italic_judge: str = "clef:27b"
    # The read model names each body page's heading and furniture lines from the page image
    # (`pageroles.py`), an input to the trees, which must be trained with it.
    page_roles: bool = False
    # The vision judge says which lines start a paragraph where it is sure
    # (`parabreaks.py`). Off: it broke more starts than it fixed (docs/design.md).
    break_judge: bool = False
    # The decision model that reads a page turn where a scene break may be lost, a page
    # that opens flush after a finished sentence, and asks the reviewer where it thinks a
    # new scene starts (`scenes.py`; "" for none). Tuning 19 questions for 10 lost breaks
    # and 2 lost chapter openings, no word moved (2026-11-24, docs/design.md).
    scene_model: str = "tokens:hf.co/mradermacher/shisa-de-1-GGUF:Q8_0"
    # The quote check's unpaired marks reach the OCR check as readings of their lines
    # (`quotes.duel_readings`), judged and decided like any other; the quote check then
    # asks nothing of its own about those paragraphs.
    quote_reader: bool = False
    # A thinking model that settles the arbiter's questions from the text around them
    # where it picks the arbiter's likeliest version (`contextjudge.py`; "" for none).
    context_model: str = ""
    # More line readers on Ollama, comma-separated ("<model>@x2" shows it each crop at
    # twice its size), whose readings the arbiter has no
    # column for: where one differs from the agreed text its version goes to the judges
    # as an offer, however poor the reader is alone (it earns its place by the silent
    # errors it reads right: `experiments/silent_screen.py`). Off until benched.
    extra_readers: str = ""
    # The arbiter's least sureness in its likeliest version for the judge to settle it:
    # where the judge agrees below this, the suspect stays asked.
    context_min: float = 0.0

    @property
    def extra_reader_models(self) -> tuple[str, ...]:
        """The readers whose readings are offers only, each as named in `extra_readers`."""
        return tuple(m.strip() for m in self.extra_readers.split(",") if m.strip())

    @property
    def alarm_models(self) -> tuple[str, ...]:
        """The second vision judges, each as named in `alarm_model` (with its `@wide`)."""
        return tuple(m.strip() for m in self.alarm_model.split(",") if m.strip())

    @property
    def alarm_votes(self) -> tuple[str, ...]:
        """The names the second judges' votes go under: as in `alarm_model`, a `@words`
        judge under its `@text` name, whose question it is asked."""
        return tuple(m.removesuffix("@words") + "@text" if m.endswith("@words") else m
                     for m in self.alarm_models)  # fmt: skip

    @property
    def hyphen_judges(self) -> tuple[str, ...]:
        """The judges of a line-end hyphen beside the judge, as named in `hyphen_judge`."""
        return tuple(m.strip() for m in self.hyphen_judge.split(",") if m.strip())

    def __post_init__(self) -> None:
        if not 0 < self.ocr_ask_below <= 1:
            raise ValueError(f"ROBO_OCR_ASK_BELOW={self.ocr_ask_below}: a probability in (0, 1]")
        if not 0 <= self.sure_heading <= 1:
            raise ValueError(f"ROBO_SURE_HEADING={self.sure_heading}: a probability in [0, 1]")
        if not 0 < self.alarm_below <= 1:
            raise ValueError(f"ROBO_ALARM_BELOW={self.alarm_below}: a confidence in (0, 1]")
        if self.ocr_questions_per_page < 0:
            raise ValueError(f"ROBO_OCR_QUESTIONS={self.ocr_questions_per_page}: not below 0")
        judges = [m for m in (self.judge_model, self.check_model, *self.alarm_models) if m]
        if len(set(judges)) < len(judges):
            # Votes are kept by model name, so two judges by one name would be one vote.
            raise ValueError(f"the judges must be different models, not {judges}")
        if self.page_roles and not (self.sorter and self.read_model):
            raise ValueError("ROBO_PAGE_ROLES feeds the trees (ROBO_SORTER) from ROBO_READ_MODEL")
        if self.read_via and not self.read_model:
            raise ValueError(
                'ROBO_READ_VIA reads in read_model\'s place, but ROBO_READ_MODEL is ""'
            )

    @classmethod
    def from_env(cls) -> "Settings":
        defaults = cls()
        return cls(
            ollama_url=os.environ.get("ROBO_OLLAMA_URL", defaults.ollama_url),
            role_model=os.environ.get("ROBO_ROLE_MODEL", defaults.role_model),
            check_model=os.environ.get("ROBO_CHECK_MODEL", defaults.check_model),
            ocr_model=os.environ.get("ROBO_OCR_MODEL", defaults.ocr_model),
            read_model=os.environ.get("ROBO_READ_MODEL", defaults.read_model),
            read_via=os.environ.get("ROBO_READ_VIA", defaults.read_via),
            page_readers=_flag("ROBO_PAGE_READERS", defaults.page_readers),
            judge_model=os.environ.get("ROBO_JUDGE_MODEL", defaults.judge_model),
            alarm_model=os.environ.get("ROBO_ALARM_MODEL", defaults.alarm_model),
            alarm_below=float(os.environ.get("ROBO_ALARM_BELOW", defaults.alarm_below)),
            hyphen_judge=os.environ.get("ROBO_HYPHEN_JUDGES", defaults.hyphen_judge),
            hyphen_learned=os.environ.get("ROBO_HYPHEN_LEARNED", defaults.hyphen_learned),
            lower_capitals=_flag("ROBO_LOWER_CAPITALS", defaults.lower_capitals),
            sure_heading=float(os.environ.get("ROBO_SURE_HEADING", defaults.sure_heading)),
            accent_doubts=_flag("ROBO_ACCENT_DOUBTS", defaults.accent_doubts),
            nested_quote_doubts=_flag("ROBO_NESTED_QUOTES", defaults.nested_quote_doubts),
            speck_doubts=_flag("ROBO_SPECK_DOUBTS", defaults.speck_doubts),
            crop_descent=_flag("ROBO_CROP_DESCENT", defaults.crop_descent),
            llama_url=os.environ.get("ROBO_LLAMA_URL", defaults.llama_url),
            fonts=os.environ.get("ROBO_FONTS", defaults.fonts),
            judge_via=os.environ.get("ROBO_JUDGE_VIA", defaults.judge_via),
            ocr_trust=_flag("ROBO_OCR_TRUST", defaults.ocr_trust),
            ocr_trust_model=os.environ.get("ROBO_OCR_TRUST_MODEL", defaults.ocr_trust_model),
            offer_trust_model=os.environ.get("ROBO_OFFER_TRUST_MODEL", defaults.offer_trust_model),
            ocr_questions_per_page=float(
                os.environ.get("ROBO_OCR_QUESTIONS", defaults.ocr_questions_per_page)
            ),
            ocr_ask_below=float(os.environ.get("ROBO_OCR_ASK_BELOW", defaults.ocr_ask_below)),
            sorter=_flag("ROBO_SORTER", defaults.sorter),
            sorter_model=os.environ.get("ROBO_SORTER_MODEL", defaults.sorter_model),
            sorter_second=os.environ.get("ROBO_SORTER_SECOND", defaults.sorter_second),
            italic_trees=_flag("ROBO_ITALIC_TREES", defaults.italic_trees),
            italic_model=os.environ.get("ROBO_ITALIC_MODEL", defaults.italic_model),
            italic_second=os.environ.get("ROBO_ITALIC_SECOND", defaults.italic_second),
            italic_judge=os.environ.get("ROBO_ITALIC_JUDGE", defaults.italic_judge),
            page_roles=_flag("ROBO_PAGE_ROLES", defaults.page_roles),
            break_judge=_flag("ROBO_BREAK_JUDGE", defaults.break_judge),
            quote_reader=_flag("ROBO_QUOTE_READER", defaults.quote_reader),
            scene_model=os.environ.get("ROBO_SCENE_MODEL", defaults.scene_model),
            context_model=os.environ.get("ROBO_CONTEXT_MODEL", defaults.context_model),
            extra_readers=os.environ.get("ROBO_EXTRA_READERS", defaults.extra_readers),
            context_min=float(os.environ.get("ROBO_CONTEXT_MIN", defaults.context_min)),
        )
