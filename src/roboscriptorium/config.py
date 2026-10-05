"""Runtime settings, overridable through environment variables."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ollama_url: str = "http://127.0.0.1:11434"
    ollaya_url: str = "http://127.0.0.1:11435"
    decision_model: str = "laya:multilingual"

    @classmethod
    def from_env(cls) -> "Settings":
        defaults = cls()
        return cls(
            ollama_url=os.environ.get("ROBO_OLLAMA_URL", defaults.ollama_url),
            ollaya_url=os.environ.get("ROBO_OLLAYA_URL", defaults.ollaya_url),
            decision_model=os.environ.get("ROBO_DECISION_MODEL", defaults.decision_model),
        )
