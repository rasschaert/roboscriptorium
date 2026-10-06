"""OCR of page regions with tesseract, for drafts a human then corrects."""

import io
import re
import subprocess
from pathlib import Path

from PIL import Image

# The Dutch model comes from tessdata_best and lives in work/tessdata; English
# ships with Homebrew's tesseract.
TESSDATA = {"nld": Path("work/tessdata")}


def language(book_language: str) -> str:
    return "nld" if book_language.lower().startswith("nl") else "eng"


def words(text: str) -> int:
    """How many tokens look like ordinary lowercase words: text read the right way up."""
    return sum(bool(re.fullmatch(r"[A-Za-z][a-z]+[.,;:!?'’”\"]*", t)) for t in text.split())


def turned(png: bytes, turn: int) -> bytes:
    """PNG bytes of an image turned `turn` degrees clockwise."""
    if not turn:
        return png
    buf = io.BytesIO()
    Image.open(io.BytesIO(png)).rotate(-turn, expand=True).save(buf, "PNG")
    return buf.getvalue()


def read_sideways(png: bytes, lang: str) -> tuple[int, str]:
    """Sideways text read upright: the turn (90 or 270 degrees clockwise) that reads, and
    the reading. Tesseract reads a vertical block either way up, so this only tells 90
    from 270."""
    readings = {t: tesseract(turned(png, t), lang) for t in (90, 270)}
    turn = max(readings, key=lambda t: words(readings[t]))
    return turn, " ".join(readings[turn].split())


def tesseract(png: bytes, lang: str, single_char: bool = False, tsv: bool = False) -> str:
    """Tesseract's text for an image, or with `tsv` its table of words with their boxes."""
    cmd = ["tesseract", "-", "-", "-l", lang]
    if single_char:
        cmd += ["--psm", "10"]
    if lang in TESSDATA:
        cmd += ["--tessdata-dir", str(TESSDATA[lang])]
    if tsv:
        # A setting, not the "tsv" config file: a --tessdata-dir without configs/ lacks it.
        cmd += ["-c", "tessedit_create_tsv=1"]
    result = subprocess.run(cmd, input=png, capture_output=True, check=True)
    return result.stdout.decode().strip()
