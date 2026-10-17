"""The context judge: a thinking model that settles OCR questions from the text around them.

A suspect the arbiter would ask about goes first to a generative model in thinking mode
(`Settings.context_model`), given the lines around its line with the place marked and
what OCR tends to confuse. Its answer is held to the versions' letters: it picks a
version, never writes one. Where it picks the version the arbiter holds likeliest, the
suspect takes that version instead of going to review; where they differ, it is asked.
A suspect whose versions the vision judge saw none of (`trust.unseen`) is left asked:
its readings missed the print. Answers are cached per book in `context-judge.json`,
keyed by the prompt.
"""

import hashlib
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from roboscriptorium.clients.ollama import OllamaClient
from roboscriptorium.files import read_cache, write_cache
from roboscriptorium.ocrcheck import Suspect
from roboscriptorium.pdf import PageText
from roboscriptorium.trust import unseen

CACHE_VERSION = 2
AROUND = 8  # lines either side of the suspect's line
LETTERS = "ABCDEFGH"

PROMPT = """You are proofreading the OCR of a printed {language} book. The OCR readings \
disagree about one place, marked ⟦?⟧ in the line marked » below. Decide which version \
the printed page shows.

Text around it, as OCR read it (other small slips are possible):
{context}

Versions for ⟦?⟧:
{versions}

Weigh grammar and meaning in context. OCR confuses look-alike \
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


def prompt(s: Suspect, pages: list[PageText], language: str) -> str:
    # Each version's count in the book is left out: given "we" 241 times against "wc" 9,
    # the judge took "we" where the sentence said wc (`experiments/probe_context_judge.py`).
    versions = [s.ours, *s.others]
    listed = "\n".join(f'{LETTERS[i]}) "{v}"' for i, v in enumerate(versions))
    name = "Dutch" if language.lower().startswith("nl") else "English"
    return PROMPT.format(language=name, context=context(pages, s), versions=listed)


def settle(
    suspects: list[Suspect],
    pages: list[PageText],
    language: str,
    likeliest: Callable[[Suspect], int],
    client: OllamaClient,
    model: str,
    cache_path: Path,
) -> list[Suspect]:
    """Copies of the suspects, each asked one settled where the judge picks the version
    the arbiter holds likeliest (`likeliest`: its index, 0 for ours). `pages` are the
    built pages the suspects index."""
    raw = read_cache(cache_path, CACHE_VERSION, model=model) or {}
    answers: dict[str, list[float]] = raw.get("answers", {})
    out = []
    for s in suspects:
        if s.choice != "review" or unseen(s) or len(s.others) + 1 > len(LETTERS):
            out.append(s)
            continue
        text = prompt(s, pages, language)
        key = hashlib.sha1(text.encode()).hexdigest()[:16]
        if key not in answers:
            answers[key] = client.choose(model, text, len(s.others) + 1)
            write_cache(cache_path, CACHE_VERSION, {"answers": answers}, model=model)
        probs = answers[key]
        best = max(range(len(probs)), key=probs.__getitem__)
        if best != likeliest(s):
            out.append(s)
        elif best == 0:
            out.append(replace(s, choice="ours", chosen=None))
        else:
            out.append(replace(s, choice="other", chosen=s.others[best - 1]))
    return out
