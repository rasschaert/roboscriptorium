"""Runtime settings, overridable through environment variables."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ollama_url: str = "http://127.0.0.1:11434"
    ollaya_url: str = "http://127.0.0.1:11435"
    decision_model: str = "laya:multilingual"
    role_model: str = "clef-flash:9b"
    # Text-only second opinion on OCR suspects, beside the role model's look at the crop.
    check_model: str = "winnow:e4b"
    # Judges the OCR check's suspects from the crop; better than role_model at that,
    # worse at line roles.
    judge_model: str = "clef:27b"
    # OCR model on Ollama for the OCR check's second reading of each line.
    ocr_model: str = "glm-ocr:bf16"
    # Learned trust (`trust.py`) chooses the OCR check's fixes and questions instead of
    # the fixed rule, asking at most this many questions per page.
    ocr_trust: bool = False
    ocr_trust_model: str = "work/models/ocr-trust.pkl"
    ocr_questions_per_page: float = 1.0

    @classmethod
    def from_env(cls) -> "Settings":
        defaults = cls()
        return cls(
            ollama_url=os.environ.get("ROBO_OLLAMA_URL", defaults.ollama_url),
            ollaya_url=os.environ.get("ROBO_OLLAYA_URL", defaults.ollaya_url),
            decision_model=os.environ.get("ROBO_DECISION_MODEL", defaults.decision_model),
            role_model=os.environ.get("ROBO_ROLE_MODEL", defaults.role_model),
            check_model=os.environ.get("ROBO_CHECK_MODEL", defaults.check_model),
            ocr_model=os.environ.get("ROBO_OCR_MODEL", defaults.ocr_model),
            judge_model=os.environ.get("ROBO_JUDGE_MODEL", defaults.judge_model),
            ocr_trust=os.environ.get("ROBO_OCR_TRUST", "") == "1",
            ocr_trust_model=os.environ.get("ROBO_OCR_TRUST_MODEL", defaults.ocr_trust_model),
            ocr_questions_per_page=float(
                os.environ.get("ROBO_OCR_QUESTIONS", defaults.ocr_questions_per_page)
            ),
        )
