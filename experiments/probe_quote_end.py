"""Is the vision reading right where it adds only a closing quote at a paragraph's end?

A quote left open at a paragraph's end is asked in the review, with the read model's
reading of the line as a proposed answer. Pieter Daens asks about a hundred of them, the
closing mark after the last stop dropped by every reader. Where the proposal is the
line with only a closing mark added at its end, is the print that line? Each tuning book
is built from its caches (as `bench` does), and each such proposal is checked against
the reference: does the reference set a closing mark right after the paragraph's last
words? No models are asked; the readings come from the caches.

    uv run python experiments/probe_quote_end.py > work/probes/quote-end.txt
"""

import re
import sys
from concurrent.futures import ProcessPoolExecutor

from roboscriptorium import bench, quotes
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring
from roboscriptorium.golden.reference import unmarked

CLOSING = "’”"
_WORD = re.compile(r"[^\W_]+")


def _key(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text)]


def _reference_end(reference: str, tail: list[str]) -> str | None:
    """The character after the paragraph's last words in the reference, past any stop."""
    words = list(_WORD.finditer(reference))
    keys = [w.group().lower() for w in words]
    n = len(tail)
    for i in range(len(keys) - n, -1, -1):
        if keys[i : i + n] == tail:
            after = reference[words[i + n - 1].end() :]
            return after.lstrip(".!?…,;: ")[:1]
    return None


def book(spec: str) -> list[tuple[str, str, str, bool | None]]:
    settings = bench.unseen(Settings.from_env(), spec.split(":")[0])
    run = scoring.build(f"work/{spec}", settings)
    reference = " ".join(unmarked(p) for ch in run.reference for p in ch.paragraphs)
    pages = {pg.number: pg for pg in run.stages.pages}
    out = []
    paragraphs = run.stages.doc.paragraphs
    for k, p in enumerate(paragraphs):
        if [w for _, w in quotes.problems(p.text)] != ["open at end"] or not p.sources:
            continue
        nxt = paragraphs[k + 1].text.lstrip()[:1] if k + 1 < len(paragraphs) else ""
        last = p.sources[-1]
        found = run.stages.quote_readings.get(last, {})
        line = pages[last.page].lines[last.line].text
        proposal = next(iter(found.values()), None)
        adds_only = (
            proposal is not None
            and proposal.rstrip()[-1:] in CLOSING
            and line.rstrip()[-1:] not in CLOSING
            and _key(proposal) == _key(line)
        )
        tail = _key(p.text)[-6:]
        end = _reference_end(reference, tail) if tail else None
        truth = None if end is None else end in CLOSING
        out.append((spec, p.text[-50:], proposal or "", adds_only, truth, nxt in "‘“"))
    return out


def main() -> None:
    # The slices as benched, from a saved run (`--run`), else today's sets.
    if "--run" in sys.argv:
        import json

        saved = json.loads(open(sys.argv[sys.argv.index("--run") + 1]).read())
        specs = [b["spec"] for b in saved["books"].values()]
    else:
        specs = bench.SETS["tuning"]
    with ProcessPoolExecutor(bench.workers()) as pool:
        rows = [r for found in pool.map(book, specs) for r in found]
    adds = [r for r in rows if r[3]]
    print(f"open at end: {len(rows)}; the proposal adds only a closing mark: {len(adds)}")
    known = [r for r in adds if r[4] is not None]
    right = sum(1 for r in known if r[4])
    print(f"of those, the reference found: {len(known)}; it closes there: {right}")
    others = [r for r in rows if not r[3] and r[4] is not None]
    print(f"open at end without such a proposal, reference found: {len(others)}; "
          f"closes there: {sum(1 for r in others if r[4])}")
    chained = [r for r in rows if r[5] and r[4] is not None]
    print(f"open at end, the next paragraph opening with a mark, reference found: "
          f"{len(chained)}; closes there in print: {sum(1 for r in chained if r[4])}")
    for spec, end, proposal, adds_only, truth, _ in rows:
        mark = {True: "closes", False: "open", None: "?"}[truth]
        print(f"{spec.split(':')[0][:30]:30} {'adds' if adds_only else '    '} {mark:6} "
              f"…{end!r} → {proposal[-40:]!r}", file=sys.stderr)


if __name__ == "__main__":
    main()
