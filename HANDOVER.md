# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session.

## State, 2026-10-11, session end

On `main`, pushed, clean. Lint and tests green. Nothing runs in `screen`.

Bench (15 tuning books, 7 validating): tuning **0.31**, validation **0.70** wrong words
a page after review (0.43 and 0.82 at midnight); paragraph breaks 0.22 and 0.21 a page.
Each change of the night is in docs/decisions.md with its numbers: the running-text
rule, Bruna's unindented paragraphs, quote questions (a lost stop, an open quote always
asked, a stray mark asked where it stands), lost drawn initials (lower case and
capitals), the judge on English line-end hyphens, no paragraph inside a broken word, a
quoted one-word line kept, an ellipsis after ? or ! spaced as read.

## What the night taught (read before choosing work)

- **About 85% of the wrong words left after review were never suspects**: every reading
  agreed, so no judge and no question saw them. The rule-sized groups are taken; each new
  rule now buys ~0.01 a page. The rest is listed per book by `experiments/unasked.py`
  (`work/probes/unasked/`, 2 min warm; 319 words over the tuning books at the last count).
- Three ways at those errors were probed on 2026-10-11, all recorded in decisions:
  a reader of the finished text (qwen3.8 proposing, clef filtering) catches about one
  error per 100 paragraphs for as many false questions, not worth building until a
  stronger text model comes (rerun `experiments/probe_text_reader.py`, ~25 min, with the
  bench's slice as the spec, e.g. `metro-2033--ia-scan:7-162:1-14`); the book's own
  spelling consistency is null (`experiments/probe_consistency.py`); Internet Archive's
  own page images cut the readers' errors by about a fifth on Crime
  (`experiments/probe_ia_images.py`) but a borrowed item offers no downloads, so not for
  Stella or the user's books.
- So accuracy moves now by readers that err less (a new model: screen it with
  `experiments/tryout.py run reader`), by measurement that can be trusted (more golden
  pairs of other kinds, verdicts), and by the reviewer.

## How to run things (learned the hard way)

- A pair of benches as one detached chain: `work/runs/compounds-chain.zsh` (edit its
  labels and log names, then `experiments/detached.sh <name> zsh <it>`); a cached pair
  takes ~10 min. Name the screen without "robo-" (detached.sh adds it).
- Don't edit `src/` while a chain runs: its second bench loads the code when it starts.
  Park a change as a patch (`git diff > work/runs/x.patch`, `git checkout`) meanwhile.
- A probe or eval on a golden book takes the bench's slice (`bench.SETS`), never the bare
  book directory: that builds the uncached pages cold.
- Probes never read the test set (Het geluid van bananen); loop over `bench.SETS["tuning"]`.
- Killing a chain's screen leaves its current step running: `pkill -f` the step too.

## Next

The open steps, in order, are in docs/checklist.md; the first ones:

1. Stella end to end: built (every stage cached) and sampled: 4 new questions, one real
   (p. 19 "féts"). Reviewed and rebuilt (epubcheck clean); the user reads the EPUB through.
2. The user's four books (Ex-minnaar, De kus in de nacht, Andere levens, Een Russische
   roman).

## Waiting on the user

- Reading Stella's EPUB through (`work/stella/stella.epub`), noting each error.
- Remove the Ollama models nothing uses: `gemma4:latest`, `deepseek-ocr:3b`,
  `numind/nuextract3:q6_k`, `imajev:4b`, `hf.co/mindchain/imajev-4b-GGUF:Q8_0`.
- **French**: undecided (under "Later" in the checklist).
- A stale worktree entry from an old session's scratchpad (`git worktree list`); the
  branch `qwen-second-look` holds the second-look probe. The remote `origin/bughunt` is
  merged and can go.
