# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session.

## State, 2026-10-11 morning

On `main`, about 45 commits ahead of `origin/main` (signed, not pushed). Lint and tests
green. Nothing runs in `screen`.

The night's chains are recorded, `bughunt` is merged (its local branch deleted; the
remote `origin/bughunt` is left), and the user asked for accuracy work from the bench
data before building Stella. Bench now (15 tuning books, 7 validating): tuning **0.31**,
validation **0.70** wrong words a page after review; paragraph breaks 0.22 and 0.21 a
page. What moved it overnight, each benched and in docs/decisions.md: the running-text
rule, Bruna's unindented paragraphs, quote questions (a lost stop, an open quote always
asked, a stray mark asked where it stands), lost drawn initials flagged, the judge on
English line-end hyphens, no paragraph inside a broken word.

The errors no question asks about are listed per book by `experiments/unasked.py`
(`work/probes/unasked/`, 2 min, warm): 319 words over the tuning books at the last count,
scattered (punctuation, word breaks, letters, quotes; docs/outlook.md has the kinds).

A detached run's chain script for a pair of benches is `work/runs/compounds-chain.zsh`
(edit its labels and log names, then `experiments/detached.sh <name> zsh <it>`). Don't
edit code under `src/` while a bench runs: the second bench of a chain loads the code
when it starts.

## Next

The open steps, in order, are in docs/checklist.md; the first ones:

1. More accuracy from the data, by size, while the user is away; the groups left are
   small (see the checklist's first step).
2. Stella end to end: build, sample the questions, the user reviews, the user reads the
   EPUB.
3. The user's four books (Ex-minnaar, De kus in de nacht, Andere levens, Een Russische
   roman).

## Waiting on the user

- Push `main` when convenient.
- Remove the Ollama models nothing uses: `gemma4:latest`, `deepseek-ocr:3b`,
  `numind/nuextract3:q6_k`, `imajev:4b`, `hf.co/mindchain/imajev-4b-GGUF:Q8_0`.
- **French**: undecided (under "Later" in the checklist).
- A stale worktree entry from an old session's scratchpad (`git worktree list`); the
  branch `qwen-second-look` holds the second-look probe.
