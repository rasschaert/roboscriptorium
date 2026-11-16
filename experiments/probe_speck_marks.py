"""A speck on the paper read as punctuation: a dot over a comma makes ";", over a full
stop ":", a fleck between two words an apostrophe ("je'vader"), one after a word a comma
(52 of the tuning bench's 460 silent errors are punctuation swapped, most of them these
in two speckled scans). No reading disputes them, so no judge sees them. Would the
drawing judge tell, were the lesser mark offered? For every body token of a book that a
speck could have made (ending ";" or ":", an apostrophe between two words, ending ","
sampled), the fit of the token as the layer has it and of the lesser version
(`rendercheck.fits`) and of the mark alone (`mark_fit`, `mark_differ`), labelled by a bench run's error rows.
`--top` lists the marks counted as printed that look least like one. No models.

    uv run python experiments/probe_speck_marks.py <run's .errors.jsonl> <book dir name> [commas sampled] [--top]
"""

import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

import pymupdf

from roboscriptorium import pipeline, rendercheck
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.pdf import cached_text_layer, line_words, page_words

CLOSERS = "'\"’”"
INNER = re.compile(r"^(\w{2,})['’‘`·](\w{2,})(\W*)$")


def lesser(token: str) -> tuple[str, str] | None:
    """The kind of mark a speck could have made of a token's, and the token without it."""
    core = token.rstrip(CLOSERS)
    tail = token[len(core) :]
    if core.endswith(";") and len(core) > 1:
        return "; for ,", core[:-1] + "," + tail
    if core.endswith(":") and len(core) > 1:
        return ": for .", core[:-1] + "." + tail
    if m := INNER.match(token):
        return "' for a space", f"{m.group(1)} {m.group(2)}{m.group(3)}"
    if core.endswith(",") and len(core) > 1 and core[-2].isalpha():
        return ", for nothing", core[:-1] + tail
    return None


def is_speck(token: str, other: str, got: str, want: str) -> bool:
    """Whether an error row says the print has the lesser version of this token."""
    if " " in other:
        return token in got.split() and other in want
    gots, wants = got.split(), want.split()
    return len(gots) == len(wants) and any(g == token and w == other for g, w in zip(gots, wants))


def main():
    errors, name = sys.argv[1], sys.argv[2]
    numbers = [a for a in sys.argv[3:] if a.isdigit()]
    commas = int(numbers[0]) if numbers else 300
    wanted = defaultdict(dict)
    for line in Path(errors).read_text().splitlines():
        e = json.loads(line)
        if e["book"] == name:
            for k in range(e["lines"][0], e["lines"][1] + 1):
                wanted[e["page"], k][e["got"]] = e["want"]
    book = Book.load(Path("work") / name)
    layer = cached_text_layer(book.source, book.stages / "textlayer.json")
    whole = [p for p in layer if book.body_pages[0] <= p.number <= book.body_pages[1]]
    judge = pipeline._alarm("render", Settings.from_env(), book, whole)
    places = []
    with pymupdf.open(book.source) as doc:
        for page in whole:
            words = line_words(page_words(doc[page.number - 1], page), page)
            for k, line in enumerate(words):
                for w in line:
                    if (found := lesser(w[4])) is None:
                        continue
                    kind, other = found
                    rows = wanted.get((page.number, k), {})
                    if any(is_speck(w[4], other, got, want) for got, want in rows.items()):
                        label = "speck"
                    elif any(w[4] in got or got in w[4] for got in rows):
                        continue
                    else:
                        label = "print"
                    places.append((kind, label, page.number, w[:4], w[4], other))
        random.seed(0)
        plain = [p for p in places if p[0] == ", for nothing" and p[1] == "print"]
        drop = set(map(id, plain)) - set(map(id, random.sample(plain, min(commas, len(plain)))))
        places = [p for p in places if id(p) not in drop]
        scored = defaultdict(list)
        for kind, label, number, box, token, other in places:
            ink = rendercheck.place_ink(doc[number - 1], box, judge._texts.get(number))
            if ink is None:
                continue
            a, b = rendercheck.fits(judge._face, judge._match.spread, judge._match.size, ink, [token, other])
            scored[kind, "whole word"].append((b - a, label, number, token, other))
            for measure in (rendercheck.mark_fit, rendercheck.mark_differ):
                got = measure(judge._face, judge._match, ink, token, other)
                if got is not None:
                    # Lower is less like the mark: negated, so a speck scores high.
                    scored[kind, measure.__name__].append((-got, label, number, token, other))
    for (kind, measure), rows in sorted(scored.items()):
        kind = f"{kind}, {measure}"
        specks = sorted(r for r in rows if r[1] == "speck")
        prints = sorted(r[0] for r in rows if r[1] == "print")
        over = sum(m > 0 for m in prints)
        print(f"{name[:28]} {kind}: {len(prints)} as printed, the lesser version fits better at {over}; {len(specks)} specks, at {sum(r[0] > 0 for r in specks)}")
        if prints:
            q = lambda f: prints[min(len(prints) - 1, int(f * len(prints)))]
            print(f"    printed marks' margin: median {q(0.5):+.3f}, 90% {q(0.9):+.3f}, 99% {q(0.99):+.3f}, most {prints[-1]:+.3f}")
        for m, _, number, token, other in specks:
            print(f"    speck p{number} {token!r} → {other!r}: {m:+.3f}, above {sum(p < m for p in prints)} of {len(prints)} printed")
        if measure == "mark_fit":
            cuts = ", ".join(
                f"under {c}: {sum(p > -c for p in prints)} printed and {sum(r[0] > -c for r in specks)} specks"
                for c in (0.5, 0.6, 0.7, 0.8)
            )
            print(f"    offered where the mark's fit is {cuts}")
        if "--top" in sys.argv:
            for r in sorted((r for r in rows if r[1] == "print"), reverse=True)[:12]:
                print(f"    as printed p{r[2]} {r[3]!r}: {r[0]:+.3f}")


main()
