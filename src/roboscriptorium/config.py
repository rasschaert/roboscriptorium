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

    @classmethod
    def from_env(cls) -> "Settings":
        defaults = cls()
        return cls(
            ollama_url=os.environ.get("ROBO_OLLAMA_URL", defaults.ollama_url),
            ollaya_url=os.environ.get("ROBO_OLLAYA_URL", defaults.ollaya_url),
            decision_model=os.environ.get("ROBO_DECISION_MODEL", defaults.decision_model),
            role_model=os.environ.get("ROBO_ROLE_MODEL", defaults.role_model),
            check_model=os.environ.get("ROBO_CHECK_MODEL", defaults.check_model),
        )
