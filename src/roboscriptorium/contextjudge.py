"""The context judge: a thinking model that settles OCR questions from the text around them.

A suspect the arbiter would ask about goes first to a generative model in thinking mode
(`Settings.context_model`), given the lines around its line with the place marked, each
version with how often the book's text layer has it, and what OCR tends to confuse. Its
answer is held to the versions' letters and read with their probabilities: it picks a
version, never writes one. Where its likeliest letter has at least `context_sure`, the
suspect takes that version instead of going to review. A suspect whose versions the
vision judge saw none of (`trust.unseen`) is left asked: its readings missed the print.
Answers are cached per book in `context-judge.json`, keyed by the prompt.
"""

import hashlib
import re
from dataclasses import replace
from pathlib import Path

from roboscriptorium.clients.ollama import OllamaClient
from roboscriptorium.files import read_cache, write_cache
from roboscriptorium.ocrcheck import Suspect
from roboscriptorium.pdf import PageText
from roboscriptorium.trust import unseen

CACHE_VERSION = 1
AROUND = 8  # lines either side of the suspect's line
LETTERS = "ABCDEFGH"

PROMPT = """You are proofreading the OCR of a printed {language} book. The OCR readings \
disagree about one place, marked ⟦?⟧ in the line marked » below. Decide which version \
the printed page shows.

Text around it, as OCR read it (other small slips are possible):
{context}

Versions for ⟦?⟧:
{versions}

Weigh grammar and meaning in context, and how this book writes the word elsewhere (the \
counts are over its whole OCR text, this place included). OCR confuses look-alike \
letters (c and e, rn and m, l, I and 1), drops or adds accents, and reads small capitals \
as mixed case ("BMw" for "BMW"). In Dutch a stress accent sits on both letters of a \
doubled vowel ("vóór", "vráág"). Choose what the page prints, even where it looks \
unusual: don't correct the author or the printer. Answer with the letter."""


def context(pages: list[PageText], s: Suspect) -> str:
    """The lines around the suspect's, across page ends, its own marked and its place
    replaced by ⟦?⟧."""
    flat = [(p.number, i, ln.text) for p in pages for i, ln in enumerate(p.lines)]
    at = next(k for k, (n, i, _) in enumerate(flat) if (n, i) == (s.page, s.line))
    marked = s.original[: s.start] + "⟦?⟧" + s.original[s.end :]
    before = [f"  {t}" for _, _, t in flat[max(0, at - AROUND) : at]]
    after = [f"  {t}" for _, _, t in flat[at + 1 : at + 1 + AROUND]]
    return "\n".join([*before, f"» {marked}", *after])


def counts(text: str, versions: list[str]) -> list[int]:
    """How often each version stands as a whole token in `text` ("Je" not inside "‘Je")."""
    return [
        len(re.findall(r"(?<!\S)" + re.escape(v.strip()) + r"(?!\w)", text)) if v.strip() else 0
        for v in versions
    ]


def prompt(s: Suspect, pages: list[PageText], book_text: str, language: str) -> str:
    versions = [s.ours, *s.others]
    listed = "\n".join(
        f'{LETTERS[i]}) "{v}": {c} times in the book'
        for i, (v, c) in enumerate(zip(versions, counts(book_text, versions), strict=True))
    )
    name = "Dutch" if language.lower().startswith("nl") else "English"
    return PROMPT.format(language=name, context=context(pages, s), versions=listed)


def settle(
    suspects: list[Suspect],
    pages: list[PageText],
    whole: list[PageText],
    language: str,
    client: OllamaClient,
    model: str,
    sure: float,
    cache_path: Path,
) -> list[Suspect]:
    """Copies of the suspects, each asked one the judge is sure of settled. `pages` are
    the built pages the suspects index; `whole` the book's whole body, for the counts."""
    raw = read_cache(cache_path, CACHE_VERSION, model=model) or {}
    answers: dict[str, list[float]] = raw.get("answers", {})
    book_text = "\n".join(ln.text for p in whole for ln in p.lines)
    out = []
    for s in suspects:
        if s.choice != "review" or unseen(s) or len(s.others) + 1 > len(LETTERS):
            out.append(s)
            continue
        text = prompt(s, pages, book_text, language)
        key = hashlib.sha1(text.encode()).hexdigest()[:16]
        if key not in answers:
            answers[key] = client.choose(model, text, len(s.others) + 1)
            write_cache(cache_path, CACHE_VERSION, {"answers": answers}, model=model)
        probs = answers[key]
        best = max(range(len(probs)), key=probs.__getitem__)
        if probs[best] < sure:
            out.append(s)
        elif best == 0:
            out.append(replace(s, choice="ours", chosen=None))
        else:
            out.append(replace(s, choice="other", chosen=s.others[best - 1]))
    return out
