"""Where both page readers (glm-ocr and Qwen, each reading the whole page) agree against
the pipeline: how many of those places are errors the review doesn't already ask about,
and how many would be questions with no need?

Uses the readings `probe_page_joins.py` cached; no models. A place counts as asked when
a question of the build (`run.found`) catches a disagreement on the same page sharing a
word with it (`quality.catches`). Paragraph breaks are left out: the page readers'
agreement on them is wrong more often than right.

    uv run python experiments/probe_page_agreement.py
"""

import re
import sys
from collections import Counter
from pathlib import Path

from rapidfuzz.distance import Levenshtein

sys.path.insert(0, str(Path(__file__).parent))
import probe_page_joins as ppj  # noqa: E402
import probe_page_reader as ppr  # noqa: E402

from roboscriptorium import bench, quality  # noqa: E402
from roboscriptorium.config import Settings  # noqa: E402
from roboscriptorium.golden import scoring  # noqa: E402

READERS = ("glm-ocr_bf16@1600000", "qwen3.8_27b-nvfp4")


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def cached(folder: str, name: str, page: int) -> list[str] | None:
    path = ppr.OUT / folder / f"{name}-{page}.txt"
    return ppr.trim(ppr.tokens_of_markdown(path.read_text())) if path.exists() else None


if __name__ == "__main__":
    settings = Settings.from_env()
    tally: Counter = Counter()
    examples: list[str] = []
    pages_read = 0
    for spec in bench.SETS["tuning"]:
        name = spec.split(":")[0]
        run = scoring.build(f"work/{spec}", bench.unseen(settings, name))
        unasked = [e for e in run.errors if not any(quality.catches(f, e) for f in run.found)]
        asked = [e for e in run.errors if any(quality.catches(f, e) for f in run.found)]
        ppr.scoring_chapters[0] = run.reference
        ref_stream = ppr.stream_of_reference(run.reference)
        ref_words, ref_pos = ppr.words_only(ref_stream)
        doc_stream = ppr.stream_of_doc(scoring.scored(run.book, run.stages))
        doc_words, doc_pos = ppr.words_only(doc_stream)
        to_doc = {}
        for op in Levenshtein.opcodes(ref_words, doc_words):
            if op.tag == "equal":
                for k in range(op.src_end - op.src_start):
                    to_doc[op.src_start + k] = op.dest_start + k
        for page, (lo, hi) in sorted(ppr.page_spans(run.stages, ref_words).items()):
            readings = [cached(f, name, page) for f in READERS]
            if any(r is None for r in readings):
                continue
            want = ppr.trim(ref_stream[ref_pos[lo] : ref_pos[hi] + 1])
            d_lo = next((to_doc[j] for j in range(lo, hi + 1) if j in to_doc), None)
            d_hi = next((to_doc[j] for j in range(hi, lo - 1, -1) if j in to_doc), None)
            if d_lo is None or d_hi is None:
                continue
            pages_read += 1
            got = ppr.trim(doc_stream[doc_pos[d_lo] : doc_pos[d_hi] + 1])
            ours = ppj.places(got, want)
            first, second = (ppj.places(r, want) for r in readings)
            here_unasked = [e for e in unasked if e.page == page]
            here_asked = [e for e in asked if e.page == page]

            def shares(text: str, errs) -> bool:
                words = _words(text)
                return any(words & (_words(e.got) | _words(e.want)) for e in errs)

            for a, b, g, w in ours:
                k = ppj.kind(g, w)
                if k == "paragraph break":
                    continue
                if any(ppj.overlaps((a, b), (c, d)) for c, d, _, _ in first + second):
                    continue  # not both page readers right here
                text = f"{g} {w}"
                if shares(text, here_unasked):
                    tally["caught, unasked", k] += 1
                    examples.append(f"{name[:18]} p{page}: «{g}» → «{w}»")
                elif shares(text, here_asked):
                    tally["caught, asked already", k] += 1
                else:
                    tally["caught, unmatched", k] += 1
            for c, d, g, w in first:
                k = ppj.kind(g, w)
                if k == "paragraph break":
                    continue
                agree = any((c, d, g) == (e, f, h) for e, f, h, _ in second)
                if agree and not any(ppj.overlaps((a, b), (c, d)) for a, b, _, _ in ours):
                    tally["false together", k] += 1

    print(f"{pages_read} pages with both readings")
    for what in ("caught, unasked", "caught, asked already", "caught, unmatched", "false together"):
        total = sum(v for (w, _), v in tally.items() if w == what)
        kinds = ", ".join(f"{k} {v}" for (w, k), v in tally.most_common() if w == what)
        print(f"  {what:22} {total:4}   {kinds}")
    print("\ncaught and unasked:")
    for e in examples[:40]:
        print(f"  {e}")
