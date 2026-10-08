"""Runtime settings, overridable through environment variables."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ollama_url: str = "http://127.0.0.1:11434"
    role_model: str = "clef-flash:9b"
    # Reads OCR suspects from the sentence, not the image. Weak alone (63% right), it is
    # kept as an alarm on the judge: clef is wrong 4% where it agrees, 22% where it
    # doesn't (docs/design.md).
    check_model: str = "winnow-ollama:e4b"
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
    # Learned trust (`trust.py`) chooses the OCR check's fixes and questions instead of
    # the fixed rule, asking at most this many questions per page.
    ocr_trust: bool = True
    ocr_trust_model: str = "work/models/ocr-trust.pkl"
    ocr_questions_per_page: float = 1.0

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
            judge_model=os.environ.get("ROBO_JUDGE_MODEL", defaults.judge_model),
            alarm_model=os.environ.get("ROBO_ALARM_MODEL", defaults.alarm_model),
            llama_url=os.environ.get("ROBO_LLAMA_URL", defaults.llama_url),
            judge_via=os.environ.get("ROBO_JUDGE_VIA", defaults.judge_via),
            ocr_trust=os.environ.get("ROBO_OCR_TRUST", "1") != "0",
            ocr_trust_model=os.environ.get("ROBO_OCR_TRUST_MODEL", defaults.ocr_trust_model),
            ocr_questions_per_page=float(
                os.environ.get("ROBO_OCR_QUESTIONS", defaults.ocr_questions_per_page)
            ),
        )
