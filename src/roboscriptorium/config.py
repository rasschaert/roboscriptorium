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
        )
