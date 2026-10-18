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
    # A second vision judge on the OCR check's suspects, served by llama.cpp at llama_url
    # (`clients/llama.py`): a vote for the arbiter, "" for none. imajev-4b disagrees with
    # clef where clef is wrong 34% of the time and where it is right 4.6% (judge set v1).
    alarm_model: str = ""
    llama_url: str = "http://127.0.0.1:8092"
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
    ocr_trust_model: str = "work/models/ocr-trust.pkl"
    ocr_questions_per_page: float = 1.0
    # Within that budget, a suspect whose likeliest version is right with at least this
    # chance (the trust model's calibrated sureness) is decided, not asked (1.0: every
    # one may be asked). 0.8 about halves the questions at the same wrong words after
    # review (docs/design.md).
    ocr_ask_below: float = 0.8
    # Line roles from trees over layout, type and the role model's answer (`sorter.py`)
    # on top of the rules in `roles.py` (docs/design.md, "Line roles").
    sorter: bool = True
    sorter_model: str = "work/models/line-roles.pkl"
    # The vision judge says which lines start a paragraph where it is sure
    # (`parabreaks.py`). Off: it broke more starts than it fixed (docs/design.md).
    break_judge: bool = False
    # A thinking model that settles the arbiter's questions from the text around them
    # where it picks the arbiter's likeliest version (`contextjudge.py`; "" for none).
    context_model: str = ""

    def __post_init__(self) -> None:
        if not 0 < self.ocr_ask_below <= 1:
            raise ValueError(f"ROBO_OCR_ASK_BELOW={self.ocr_ask_below}: a probability in (0, 1]")
        if self.ocr_questions_per_page < 0:
            raise ValueError(f"ROBO_OCR_QUESTIONS={self.ocr_questions_per_page}: not below 0")
        judges = [m for m in (self.judge_model, self.check_model, self.alarm_model) if m]
        if len(set(judges)) < len(judges):
            # Votes are kept by model name, so two judges by one name would be one vote.
            raise ValueError(f"the judges must be different models, not {judges}")
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
            llama_url=os.environ.get("ROBO_LLAMA_URL", defaults.llama_url),
            judge_via=os.environ.get("ROBO_JUDGE_VIA", defaults.judge_via),
            ocr_trust=_flag("ROBO_OCR_TRUST", defaults.ocr_trust),
            ocr_trust_model=os.environ.get("ROBO_OCR_TRUST_MODEL", defaults.ocr_trust_model),
            ocr_questions_per_page=float(
                os.environ.get("ROBO_OCR_QUESTIONS", defaults.ocr_questions_per_page)
            ),
            ocr_ask_below=float(os.environ.get("ROBO_OCR_ASK_BELOW", defaults.ocr_ask_below)),
            sorter=_flag("ROBO_SORTER", defaults.sorter),
            sorter_model=os.environ.get("ROBO_SORTER_MODEL", defaults.sorter_model),
            break_judge=_flag("ROBO_BREAK_JUDGE", defaults.break_judge),
            context_model=os.environ.get("ROBO_CONTEXT_MODEL", defaults.context_model),
        )
