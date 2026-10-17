# Hosted inference: a plan for a free window

What to do if the user gets a stretch of free hosted inference: what to learn from it,
what carries back to the local build and what doesn't, and the guardrails. Written
2026-10-17, when a Belgian AI start-up (EU data sovereignty, solar-powered) offered
attendees of its launch a month of free inference. Nothing here runs until the user has
access and approves each run: AGENTS.md's "Local first" rule holds as it stands.

## What the earlier hosted runs taught (2026-10-08 to 10-10, docs/decisions.md)

- **The same model reads nearly the same on a datacenter GPU and on the Mac.** Qwen3.8
  27B at bf16 (DeepInfra, via OpenRouter) and the local nvfp4 build gave the same
  reading on 94.5–97.6% of lines (CER 0.11% against 0.10% on Goede dochter pp. 9–20).
  A finding about what a model *can do* carries over.
- **The host matters more than the chip.** Hosted clef judged differently from the local
  one (Cloudflare 96.2% the same pick); PrimeIntellect's barely read the image;
  Darkbloom's fp4 Qwen read worse than the text layer. Every hosted build is measured
  against the local one before its results count.
- **Hosted output must not leak into what the local build learns from.** For a while the
  bench and the trust data were built on hosted readings, so the arbiter trained on a
  reader Stella's build doesn't use; Qwen went back to reading locally on 2026-10-09.
- **Hosts go down without saying so.** DeepInfra's Qwen hung a run for half an hour
  while its status page said operational: requests get a deadline on the whole request.

## What carries back, and what doesn't

Carries back: whether an *idea* works (a whole-page reading, a stage left out, a model
doing a stage's job); how far the best open models are ahead; labelled data; models
trained on that data.

Doesn't: thresholds, calibrated confidences, any number tuned to one build. Precision
(bf16 or fp8 there, nvfp4 or Q8 here), the serving stack's image resizing (vLLM and
Ollama see different pixels), sampling defaults and batching all differ. So the window
is for answering questions, not for tuning settings; whatever wins is confirmed locally
once, on the frozen sets and then the bench.

## What to use it for, by expected gain

1. **The gap to the best open readers.** The ceiling probe (decisions.md, 2026-10-15)
   had Claude read 17 pages with one real error where local Qwen made 76 wrong words.
   Whole-page reading is the architecture to aim for (docs/outlook.md); what's missing is
   a local reader close enough. Run the largest open vision models the host serves, the
   ones that don't fit in 64 GB, on the same pages (`experiments/probe_page_reader.py`)
   and on the reader set (`experiments/tryout.py run reader`). If a large open model
   comes close to Claude, the gap is size: wait for smaller models to catch up, or for
   more memory. If none does, no open model can do it yet.
2. **Labels, so the local decision models learn more.** The trees and the arbiter learn
   from the golden books and the reviewer's answers only. A strong model could label
   line roles, paragraph breaks and page kinds over many more pages (the AI-usage
   section in AGENTS.md allows labelling with a large generative model where there is
   no reference). Measure its labels against the golden pages first, since its errors
   become ours. The trained local models stay after the window closes: the lesson most
   likely to last.
3. **The assumptions to test, fast.** A cold bench is a night here; hosted, the same
   probe takes minutes. The checklist's "Assumptions to test" and the outlook's untried
   ideas (a page-level reading of paragraph breaks, for one) are the queue. Each winner
   is confirmed locally.
4. **Fine-tuning a small local reader,** only if the host offers training, not just
   inference. The outlook keeps fine-tuning off for now; a strong model's labels and
   free GPU time are what would change that.

## Guardrails

- **Copyright.** Sending page images to a host is the user's call per use, whatever the
  host's sovereignty. Read the free tier's terms first: whether prompts are kept or
  trained on (a host that keeps them is refused, as on OpenRouter). The public-domain
  pairs, the only ones without `eu_copyright_until` in their manifest, are The Nature
  of a Crime and Doctor Dolittle; every other golden book and Stella is in copyright.
- **Separate caches.** Hosted output is cached under its own build's name, never under a
  local model's, and enters trust data or the bench only marked as hosted (the bench's
  `read_via` share shows it).
- **A pair awaiting its first look stays untouched**, as everywhere.
- **Pinned like OpenRouter:** one model at one precision, no fallback, measured against
  the local model first. `clients/openrouter.py` and `ROBO_READ_VIA` / `ROBO_JUDGE_VIA`
  (`config.py`) are the pattern; an OpenAI-compatible API needs little more than a new
  base URL and key.
- **A free month is short.** Prepare the probes before access starts, so no free day
  goes to setup.

## Ask the user for, once access comes

The models served (vision ones above all) and at what precision; the terms on keeping
prompts; the API's shape; rate limits; whether it offers fine-tuning; the window's end
date.
