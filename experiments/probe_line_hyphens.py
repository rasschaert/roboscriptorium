"""Every hyphen at a line's end in the tuning books' slices, decided by `reflow.join`'s
rule and by candidate rules, scored against the reference where it spells the word one
way only. No models: the text layer, the word list and the derived reference.

    uv run python experiments/probe_line_hyphens.py
"""

import re
from collections import Counter
from pathlib import Path

from roboscriptorium import bench, ocr, reflow
from roboscriptorium.book import Book
from roboscriptorium.cli import _range
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.lexicon import Lexicon
from roboscriptorium.pdf import cached_text_layer

W = re.compile(r"[^\w-]")


def rules(known, lang):
    def old(nxt, stem, rest, seen):
        return reflow._hyphen_stays(nxt, stem, rest, seen, known)

    def parts(nxt, stem, rest, seen):
        # Both sides words of their own, the closed form unknown: a compound's hyphen.
        if (
            old(nxt, stem, rest, seen) is False
            and "-" not in stem + rest
            and not seen[f"{stem}{rest}".lower()]
            and not known(stem + rest)
            and min(len(stem), len(rest)) >= 3
            and known(stem)
            and known(rest)
        ):
            return True
        return old(nxt, stem, rest, seen)

    def name(nxt, stem, rest, seen):
        # A capitalised first part the word list doesn't know in lower case, the rest a
        # word: a name joined to a word ("Tokugawa-shoguns").
        if (
            old(nxt, stem, rest, seen) is False
            and stem[:1].isupper()
            and not stem.isupper()
            and not known(stem.lower())
            and not known(stem + rest)
            and len(rest) >= 3
            and known(rest)
        ):
            return True
        return old(nxt, stem, rest, seen)

    return {"old": old, "parts": parts, "name": name}


score = {}
for spec in bench.SETS["tuning"]:
    name, pages, chapters = (spec.split(":") + ["", ""])[:3]
    book = Book.load(Path("work") / name)
    first, last = _range(pages or None) or book.body_pages
    lang = ocr.language(book.language)
    layer = cached_text_layer(book.source, book.stages / "textlayer.json", lang)
    layer = [p for p in layer if first <= p.number <= last]
    seen = reflow.spellings(layer)
    lex = Lexicon.load(lang)
    ref = load_chapters(Golden.load(book.golden).text_dir)
    words = Counter(
        W.sub("", w).lower() for ch in ref for para in ch.paragraphs for w in para.split()
    )
    lines = [line.text for p in layer for line in p.lines]
    for rule_name, rule in rules(lex.knows, book.language).items():
        for text, nxt in zip(lines, lines[1:]):
            if not (text.endswith(reflow.HYPHENS) and len(text) > 1 and text[-2].isalpha()):
                continue
            stem = W.sub("", text.split()[-1][:-1])
            rest = W.sub("", nxt.split()[0]) if nxt.split() else ""
            if not stem or not rest:
                continue
            hyph, closed = words[f"{stem}-{rest}".lower()], words[f"{stem}{rest}".lower()]
            if bool(hyph) == bool(closed):
                continue
            truth = bool(hyph)
            got = rule(nxt, stem, rest, seen)
            key = (book.language, rule_name)
            s = score.setdefault(key, Counter())
            s["right" if got == truth else "wrong"] += 1
            if got != truth and rule_name != "old":
                s[f"wrong {'kept' if got else 'joined'}"] += 1
                if s[f"shown {got}"] < 8:
                    s[f"shown {got}"] += 1
                    print(f"  {rule_name:5} {book.language} {name[:14]:14} {stem}-{rest}: kept={got}, ref {'hyphen' if truth else 'closed'}")
for key, s in sorted(score.items()):
    print(key, dict(s))
