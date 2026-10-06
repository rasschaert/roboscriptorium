"""OCR of page regions with tesseract, for drafts a human then corrects."""

import subprocess
from pathlib import Path

# The Dutch model comes from tessdata_best and lives in work/tessdata; English
# ships with Homebrew's tesseract.
TESSDATA = {"nld": Path("work/tessdata")}


def language(book_language: str) -> str:
    return "nld" if book_language.lower().startswith("nl") else "eng"


def tesseract(png: bytes, lang: str, single_char: bool = False, config: str = "") -> str:
    """Tesseract's text for an image; `config` names another output, such as "tsv"."""
    cmd = ["tesseract", "-", "-", "-l", lang]
    if single_char:
        cmd += ["--psm", "10"]
    if lang in TESSDATA:
        cmd += ["--tessdata-dir", str(TESSDATA[lang])]
    if config:
        cmd.append(config)
    result = subprocess.run(cmd, input=png, capture_output=True, check=True)
    return result.stdout.decode().strip()
