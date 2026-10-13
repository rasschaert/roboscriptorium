"""glm-ocr's whole-page reading as one more reader: on the tuning slices, where would it
disagree with the pipeline's output, and how often would that disagreement point at a
real error?

Every slice page is scored without models first (`probe_page_reader`'s page stretches);
glm-ocr then reads each page holding a pipeline error and a sample of clean ones. Per
place, in reference words:

- caught: the pipeline is wrong and glm-ocr reads it right (a question with the answer),
- both wrong: the pipeline is wrong and so is glm-ocr there,
- false alarm: glm-ocr is wrong where the pipeline is right (a question with no need),

each by kind of error (`quality.category`). Pages under 60 reference words are left
out: glm-ocr invents text on near-empty pages. Needs Ollama's context at 32k for
glm-ocr at full size (GLM_PIXELS=1600000).

    GLM_PIXELS=1600000 uv run python experiments/probe_page_joins.py [clean sample]

With SECOND=<model> (Qwen, say), a second page reader reads the same pages, and the
tally adds the places where both page readers are right against the pipeline (caught
together) and where both are wrong alike where the pipeline is right (false together).
"""

import os
import random
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from rapidfuzz.distance import Levenshtein

sys.path.insert(0, str(Path(__file__).parent))
import probe_page_reader as ppr  # noqa: E402

from roboscriptorium import bench, pdf, quality  # noqa: E402
from roboscriptorium.config import Settings  # noqa: E402
from roboscriptorium.golden import scoring  # noqa: E402

MODEL = "glm-ocr:bf16"
SECOND = os.environ.get("SECOND", "")
MIN_WORDS = 60


def places(got: list[str], want: list[str]) -> list[tuple[int, int, str, str]]:
    """Where `got` differs from `want`: (start, end) in `want`, and both sides' text."""
    out = []
    for op in Levenshtein.opcodes(got, want):
        if op.tag != "equal":
            out.append(
                (
                    op.dest_start,
                    op.dest_end,
                    " ".join(got[op.src_start : op.src_end]),
                    " ".join(want[op.dest_start : op.dest_end]),
                )
            )
    return out


def overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    # An insertion has an empty span; it overlaps what it touches.
    return a[0] <= b[1] and b[0] <= a[1]


def kind(got: str, want: str) -> str:
    return quality.category(SimpleNamespace(got=got.replace("¶", "").strip(), want=want.replace("¶", "").strip())) if (got.replace("¶", "").strip() or want.replace("¶", "").strip()) else "paragraph break"  # noqa: E501


if __name__ == "__main__":
    sample = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    settings = Settings.from_env()
    pages = []  # (spec, name, page, want, pipeline tokens)
    for spec in bench.SETS["tuning"]:
        name = spec.split(":")[0]
        run = scoring.build(f"work/{spec}", bench.unseen(settings, name))
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
            want = ppr.trim(ref_stream[ref_pos[lo] : ref_pos[hi] + 1])
            if len(want) < MIN_WORDS:
                continue
            d_lo = next((to_doc[j] for j in range(lo, hi + 1) if j in to_doc), None)
            d_hi = next((to_doc[j] for j in range(hi, lo - 1, -1) if j in to_doc), None)
            if d_lo is None or d_hi is None:
                continue
            got = ppr.trim(doc_stream[doc_pos[d_lo] : doc_pos[d_hi] + 1])
            pages.append((run.book.source, name, page, want, got))
    erring = [p for p in pages if places(p[4], p[3])]
    clean = [p for p in pages if not places(p[4], p[3])]
    random.Random(0).shuffle(clean)
    chosen = erring + clean[:sample]
    print(f"{len(pages)} pages, {len(erring)} with a pipeline error; reading {len(chosen)}")

    tally: Counter = Counter()
    examples: dict[str, list[str]] = {}
    def reading(model: str, source, name: str, page: int) -> list[str]:
        glm = model.startswith("glm-ocr")
        pixels = ppr.GLM_PIXELS if glm else 1_600_000
        folder = model.replace(":", "_") + (f"@{pixels}" if glm else "")
        cache = ppr.OUT / folder / f"{name}-{page}.txt"
        if cache.exists():
            text = cache.read_text()
        else:
            png = pdf.render_png(source, page, max_pixels=pixels)
            text, _ = ppr.read_page(model, png, settings.ollama_url)
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(text)
        return ppr.trim(ppr.tokens_of_markdown(text))

    for source, name, page, want, got in chosen:
        glm = reading(MODEL, source, name, page)
        ours, theirs = places(got, want), places(glm, want)
        if SECOND:
            other = places(reading(SECOND, source, name, page), want)
            for a, b, g, w in ours:
                k = kind(g, w)
                hit = lambda errs: any(overlaps((a, b), (c, d)) for c, d, _, _ in errs)  # noqa: E731
                if not hit(theirs) and not hit(other):
                    tally["caught together", k] += 1
            for c, d, g, w in theirs:
                same = any((c, d, g) == (e, f, h) for e, f, h, _ in other)
                if same and not any(overlaps((a, b), (c, d)) for a, b, _, _ in ours):
                    tally["false together", kind(g, w)] += 1
        for a, b, g, w in ours:
            k = kind(g, w)
            if any(overlaps((a, b), (c, d)) for c, d, _, _ in theirs):
                tally["both wrong", k] += 1
            else:
                tally["caught", k] += 1
                examples.setdefault(k, []).append(f"{name[:18]} p{page}: «{g}» → «{w}»")
        for c, d, g, w in theirs:
            if not any(overlaps((a, b), (c, d)) for a, b, _, _ in ours):
                tally["false alarm", kind(g, w)] += 1
        print(f"{name[:30]:30} p{page:<4} pipeline {len(ours):2}  glm {len(theirs):2}", flush=True)

    n = len(chosen)
    print(f"\nover {n} pages ({len(erring)} with a pipeline error, {n - len(erring)} clean):")
    for what in ("caught", "both wrong", "false alarm", "caught together", "false together"):
        total = sum(v for (w, _), v in tally.items() if w == what)
        kinds = ", ".join(f"{k} {v}" for (w, k), v in tally.most_common() if w == what)
        print(f"  {what:12} {total:4}   {kinds}")
    print("\ncaught, by kind:")
    for k, ex in examples.items():
        for e in ex[:6]:
            print(f"  {k:14} {e}")
