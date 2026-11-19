# Handover

The state of play for the next session: what runs, what comes next, what waits on the
user. Nothing else lives here (AGENTS.md says which file owns what). Rewrite it at the
end of every session. **Read the first section; it is complete and current.** The
sections below it are older (each says its date) and are superseded wherever the first
section speaks: baselines, what runs, what is on by default.

**State at 20:35 on 2026-11-19** (a new session, "continue"). Below it, the 06:35 state
still holds where this doesn't speak.

- **Running:** `robo-arete-groot`, Groot 19B and Arete-27B Q4 as two more text judges
  (offers off), resumed at 20:05 from its saved answers; Groot finished Goede dochter,
  then Arete (done 21:50). Re-estimated from Goede dochter (4,776 of the run's 43,215
  questions a judge; Arete 1.6 h, Groot 0.3 h for it): about 15 more hours of judging,
  then training and both benches, ending about 15:00 on 2026-11-20; watcher on `work/runs/arete-groot.out`, the
  rebuild's `work/probes/ocr-trust-ag/runs/progress.txt` and the books' saved answers.
  Its validation bench compares against `030945`, whose Vanille had a stale ellipsis
  style: read it against `validation-20261119T191549-e435710` (the fresh offers-off
  baseline) with `bench-diff`.
- **Queued behind it:** `robo-cache-code-bench`, both sets warm with the branch
  `cache-code` (a cache measured on the scan is keyed by its code; a crash-emptied cache
  is remade), models unreachable; merge it into main if no word moves. Watcher on
  `work/runs/cache-code-bench.out`.
- **Settled tonight:** validation's 39 words fixed and 29 made were Vanille's ellipsis
  style served from the cache of a method reverted on 2026-10-24 (decisions.md); the
  offers change no validation word against the fresh baseline, 6 more questions. New
  engineering rule in AGENTS.md: a change in how a cached value is found bumps its
  cache's version, its revert too.

**State at 06:35 on 2026-11-19** (the user packing up; every run stopped, nothing running
but `robo-battery-guard`).

- **Taken tonight** (decisions.md has each with its fixes and errors): the quote fix (a
  single-quoted book's ‘ read as "); Vanille's chapter numbers over titles; a running head
  holding its page's number on one other page; a full stop and an ellipsis as the print's
  four spaced dots; Dolittle's ellipsis style from its stops' spaced dots (14 words
  fixed); Dutch line-end hyphens by the learned decision for plain words; the hyphen
  cache keeping each judge's answers; **accent and speck offers on by default** (the
  user's call; benched again with their arbiter held out per book, which the first count
  wasn't: tuning 17 silent errors asked for 40 more questions, validation none for 5).
- **Not taken:** the grown-slice line-role trees as the first set (unnumbered section
  titles kept as text); Surya's layout columns parked with them; a page-number column
  for the trees (null). Tess, Arete and Groot as readers: no seat.
- **Production baselines** (`work/probes/production-baseline/`): tuning
  `work/bench/tuning-20261119T045526-950d1bf-dirty.json`, validation
  `work/bench/validation-20261119T051238-9d6c170-dirty.json` (offers on).
- **Waiting on the user:** nothing.

**State at 13:30 on 2026-11-18** (after the user's computer crashed at about 02:11, 4 books
into `robo-hyphen-panel2`'s tuning bench). The whole queue below was restarted at 13:15
in its order, each run resuming from its caches; Ollama 0.40.16, `doctor` clean. New:
`robo-battery-guard` (`experiments/battery_guard.sh`) stops the runs under 30% battery
and continues them at 50% (the user is on a charger under 140 W). Watchers on the queue
and the guard. Since: the hyphen panel benched NO CHANGE (decisions.md); Tess-4.5-27B as a
reader rescues 20 of 97 silent lines (book and zoom crops), none that no screened reader
brings, 2 the readers in use miss (stress accents, both brought by Arete and Groot); its
judge tryout runs (`work/runs/tess-q8-judge.log`), then `experiments/vote_sim.py` on it,
then its models.md entry (done: it repeats Arete; the reading vote queued for Tess,
Arete and Groot, `reader-votes.sh`). The learned hyphen decision benched tuning BETTER,
validation NO CHANGE, and is on by default (merged `hyphen-learned`); **production
baselines now** `work/bench/tuning-20261118T195052-dc2d097-dirty.json` and
`work/bench/validation-20261118T195151-f816977-dirty.json`. On the 140 W charger since
20:30; the queue: `robo-surya-layout-all` (took the lock at 20:51, about six hours), then
`robo-quote-straight` and `robo-reader-votes`, then `robo-surya-roles`.

**State at 23:35 on 2026-11-17** (a new session, "continue"). Below it, the 09:40 state
still holds where this doesn't speak.

- **Queue** (one model job at a time, `work/runs/model-screen.lock`), started 23:36–23:45:
  1. ~~`robo-quote-stray`~~ done 23:58 (decisions.md).
  2. ~~`robo-surya`~~ done 23:55 (`work/runs/surya-screen.sh`): Surya OCR 2 (the user's pull) as a reader
     on the silent-error lines with its own prompt, then its layout on 212 pages where
     the line-role trees err (`experiments/probe_surya_layout.py`): rescues of headings
     and furniture, e.g. Vanille's chapter numbers, which the trees call furniture.
  3. ~~`robo-offers-together`~~ done 02:05: 19 of tuning's silent errors asked for 38
     questions, validation 4 questions for none; **the user's call** (checklist).
     New production baselines: `tuning-20261117T230103`, `validation-20261117T230206`.
  4. `robo-hyphen-panel2` (`work/runs/hyphen-panel2.sh`): the four hyphen judges by their
     mean again, now shown the break as the question says (`be00196`), against the offers
     run's baselines.
  4b. `robo-hyphen-learned` (`work/runs/hyphen-learned.sh`): the learned hyphen decision
     (branch `hyphen-learned`, worktree `../robo-hyphen-learned`) trained on the panel
     run's caches, both benches.
  4c. `robo-quote-straight` (`work/runs/quote-straight.sh`): a single-quoted book's ‘
     read as a straight " mended (branch `quote-straight`, worktree
     `../robo-quote-straight`): De kus's 16 paragraphs; watch Het geluid van bananen's
     "“Alternatieve Asjoera’*”", which it would flip wrongly.
  5. `robo-tess-q8`, started by a wait on the user's pull of Tess-4.5-27B Q8_0
     (`work/runs/tess-q8-screen.sh`); takes the lock when free.
- **The hyphen question's form:** the judges were shown "rechtbank-|fantasie" (hyphen and
  break mark); hidden since `be00196`. That cost English 10 silent words on tuning (the
  shown hyphen was a useful prior there; decisions.md 2026-11-18). Left as is while the
  offers run uses it; after the hyphen runs, choose the form per language.
- **Quote change:** asking at a paragraph's unpaired opening mark taken out (De geruchten's
  questions rose for nothing); the stray opening offered to the judges kept.
- **Surya OCR 2:** as a reader 12 of 97 silent lines, 1 no other reader rescues; as a
  spotter 48 of the line-role trees' 243 wrong lines labelled right (models.md).
  Queued last: `robo-surya-layout-all` (`work/runs/surya-layout-all.sh`), its layout on
  all 7,006 labelled pages (about six hours), after the hyphen panel; then its labels as
  tree features, each book left out (no models).
- **Speck offers on their own arbiter** (done 23:33): 4 of 52 silent rescued as questions,
  none made, NO CHANGE both (decisions.md).
- **Baselines now:** tuning `work/bench/tuning-20261117T222142-c6a13c4-dirty.json` (Au pair
  with `doubled_singles`), validation `validation-20261117T020028-90f9f02-dirty.json`.
- **Done this session:** the user's short reviews of 2026-11-16 were all answered; Au
  pair's reference sets the print's double marks (21 wrong words fixed on tuning); a
  bench outlives one book's failure (retried alone, else left out and named); Het geluid
  van bananen's extra italic error is the retrained arbiter's split ellipsis.

**State at 09:40 on 2026-11-17: the session ended at the user's word.** decisions.md,
2026-11-16 and 17, has every number.

- **Nothing runs.** No screen, no model loaded, no watcher, the tree clean and pushed
  (`4614e02`).
- **Baselines** (the line-role referee on): `work/bench/tuning-20261117T015939-90f9f02-dirty.json`
  and `work/bench/validation-20261117T020028-90f9f02-dirty.json`. Every baseline named
  further down is older.
- **Waiting on the user, one call (benched together 2026-11-18, see the queue above):** accent and speck offers on by default? The older note: Stress accents measured
  on the scan are offered as versions and decided by an arbiter of their own. On tuning
  15 of 74 silent accent errors become questions (none fixed, none made) for 37 more
  questions; on validation 5 more questions and none of 8 caught. Both benches NO CHANGE.
  On main, off: `ROBO_ACCENT_DOUBTS=1 ROBO_OFFER_TRUST_MODEL=work/models/ocr-trust-accents-apart.pkl`.
- **Answered (checked 23:10):** the short reviews they started at about 17:00 on
  2026-11-16 (Au pair's 16 small-capital places; 9 accent additions in Goede dochter and
  De vergelding). Check the verdict files before asking. Au pair's manifest gets
  `doubled_singles = true` after them, then a new tuning baseline.

**Taken this session**
- **The line-role referee, on by default** (`sorter_second`, `work/models/line-roles-second.pkl`;
  `ROBO_SORTER_SECOND=` turns it off; the tests turn it off in `tests/conftest.py`):
  clef 27B looks at the whole page where two sets of line-role trees call a line
  differently, about one line in 700. Tuning BETTER (75 fixed, 18 made, heading errors
  24 → 18), validation BETTER (52 → 48). Costs on the record: 3 silent errors made on
  tuning ("(Intermezzo)" lost in Reis om mijn schedel), 1 on validation, 6 punctuation.
- **The heading count** (`evaluate._same_heading`, `_match_headings`): a title found
  without its number, or a title and subtitle set as two headings, is found but not
  exact: one error, not two.
- **De kus in de nacht built again:** 814 → 518 questions (425 OCR doubts, 113 quotes).
  Not ready for review: three classes of quote question the machine should settle are on
  the checklist (a straight `"` for an opening ‘, speech opening on ’t, 22 quote questions
  with no quote mark); then sample again.

**Not taken as built; each has its reason and its next version on the checklist**
- Arbiters retrained with accent, nested-quote and speck offers: the retraining itself
  costs punctuation, whatever the offers do. Hence the offers' own arbiter (above); speck
  offers on an arbiter of their own is the open version (5 of 52 silent specks rescued).
- Hyphen judges by their mean (`ROBO_HYPHEN_JUDGES`, off): 29 of 74 rescued, 44 made; the
  mean doesn't separate right from wrong. Next: keep each judge's chance (the cache drops
  them once the mean is made, `hyphens.Compounds`), learn the combination, ask the
  undecided.
- Nested-quote offers: rescue nothing. Of the five silent places, the judges are split or
  unsure on four and the arbiter fails the fifth (‘“Lucy). Next: an enlarged crop of the
  offered mark for the judges; `quotemarks.py`'s measure on the places with no offer.

**Models screened** (docs/models.md; all three pulled and on Ollama)
- Arete-27B Q4 and Q6 as readers rescue the same 3 silent lines ("míjn", "bètahoek",
  "old...."); Q6 is no better than Q4. Groot 19B rescues ‘“Lucy alone but changes 17–18 of
  48 clean lines. All readers together 36 → 40 of 97 silent lines.
- As judges, the panel's lift: Arete Q4 +0.005 [−0.000, +0.010], Q6 +0.003, Groot +0.004;
  Q4, Q6 and Groot together +0.007 [+0.000, +0.015].
- **The run that settles them, not started: explain it to the user first, it is hours.**
  Trust data with Arete Q4 and Groot as extra text judges, an arbiter on it, a control
  arbiter retrained on today's data beside it, both benches; and Groot's readings as
  offers through the judges (`ROBO_EXTRA_READERS`). Write its script with `# resumes:`,
  `# models:` and `# one at a time:`; the judges asked one model over all its questions.
  `work/runs/model-screen.sh <ollama model> <tag>` screens a further model the same way.

**To do next, no models, in this order** (each an open step on docs/checklist.md)
1. A bench that outlives one book's failure and picks its own number of books at once
   (the referee's bench died at 15 of 20 books on one `httpx.ReadTimeout`).
2. Hyphen judges: keep each judge's chance, learn the combiner.
3. Which italic word an accent offer adds in Het geluid van bananen.
4. De kus in de nacht's three quote-question classes.
5. Vanille's chapter numbers beside its titles (4 of 15 headings found).

**How the machine behaves, learned the hard way this session**
- Ollama won't load a second large model beside a bench's judge; it marks the first
  "Stopping..." while it keeps serving. Model tests wait behind benches.
- Several large models asked in turn reload at every call: group calls by model.
- Six books at once time a cold judge out: `ROBO_BENCH_WORKERS=1` for a cold bench.
- `experiments/detached.sh` refuses a run script without `# resumes:` and `# models:`, and
  above 48 GB without `# one at a time:`.
- The prompt hook (`.claude/hooks/purpose-check.sh`, outside git) has five checks; the
  fourth is "a verdict gives its rescues first" (AGENTS.md, "Judged by its rescues";
  `experiments/offer_rescues.py <baseline errors.jsonl> <new errors.jsonl>`,
  `experiments/judge_lift.py`), the fifth the stop test before a run.

**Worktrees:** `../robo-offer-arbiter` (branch `offer-arbiter`, merged: can go);
`../robo-render` (`render-differ`, kept), `../robo-cols` (`render-columns`, kept),
`../robo-kern` (`render-kern`, not merged); `../robo-spacing`, `../robo-grow6`,
`../roboscriptorium-caps` (merged: can go); `-py315` two untracked scratch files.

**State at 02:20 on 2026-11-16** (the user checked in at 01:00: "keep at it"; the
confirmations below wait for a later moment, to be brought up again). Since 20:45:
- The short bench of the extra readers ended at 06:24 on 2026-11-16 (nine hours): no
  change overall, 3 wrong words fixed and 11 made, 11 more questions, the arbiter not
  retrained for them (decisions.md). Not on: 4 of their 362 offers were the print
  (`probe_extra_offers.py`); only offers both readers agree on look worth a test. The accent run started at 07:25; the queue follows by itself.
- The accent run ended 12:07 on 2026-11-16: not taken as it stands (tuning silent
  460 → 458 for 106 more questions; validation worse). Cause: the arbiter's one count
  per substitution pooled the offers with the readers' accents. Built: versions no
  reading has counted apart (`trust.UNREAD`; saved arbiters unchanged). Running:
  `robo-accents-apart` (`work/runs/accents-apart.sh`): that arbiter trained on the accent
  run's data (no models), then both benches once `robo-accents-mark` and `robo-nested`
  are done; those two now train the same way. `robo-hints` ran nothing the first time
  (a flag passed as one word), fixed and queued behind `robo-sorter-panel` as `robo-prompt-hints` (under its old name the judge probes, which wait for a run called `robo-hints`, and it waited on each other from 12:52 to 15:29).
- Specks read as punctuation (most of tuning's 52 silent punctuation swaps): the drawn
  mark's own fit ranks them (`experiments/probe_speck_marks.py`, `work/runs/speck-marks.log`
  over every tuning book). Built, off: `speckmarks.py` (`ROBO_SPECK_DOUBTS`), the mark's
  own ink against the book's other pictures of it: 461 offers over tuning, 16 named
  specks among them. Queued: `robo-speck-chain` (`work/runs/speck-chain.sh`), behind
  `robo-accents-mark`, `robo-nested` and `robo-accents-apart`: both production benches
  on today's code as the baseline (kept in `work/probes/speck-baseline/`), then trust
  data `work/probes/ocr-trust-specks/`, arbiter and both benches.
- Hyphen judges together (`ROBO_HYPHEN_JUDGES`, off): built after the probe; queued
  `robo-hyphen-panel` (`work/runs/hyphen-panel.sh`), both benches against the speck run's
  baseline, behind `robo-speck-chain`.
- Line roles: a referee between two sets of trees built, off (`ROBO_SORTER_SECOND`,
  `sorter.Referee`); queued `robo-sorter-referee` (`work/runs/sorter-referee.sh`), last.
- 2026-11-16 19:50: `robo-accents-apart` and `robo-nested` ended, both not taken (decisions.md:
  the offers work, the retrained arbiter costs punctuation). Queued last: `robo-offer-arbiter`
  (`work/runs/offer-arbiter.sh`): the offers decided by their own arbiter, production's
  everywhere else (branch `offer-arbiter`, worktree `../robo-offer-arbiter`, off by default).
  An agent session picked up all five screens and watches them (Monitor, re-armed every 30 min).
- 2026-11-16 23:00: the user wants Arete-27B tried (NousResearch's post-trained Qwen3.8-27B, the read model's base). Queued: `robo-arete-screen` (`work/runs/arete-screen.sh`), which waits for the user's pull (`ollama pull hf.co/bartowski/NousResearch_Arete-27B-GGUF:Q4_K_M`) and the benches, then screens it by its rescues as a reader and on the judge set. Verdict to models.md.
- The page-kind model is told each back page's ink (last end right 22 → 24 of 27).
- The user started the short reviews at about 17:00 on 2026-11-16 (Au pair's 16
  small-capital places, 9 accent additions in Goede dochter and De vergelding).
- `init`'s fields scored against the publishers' e-books (`score_init.py`): the e-books'
  metadata is the weaker side at most misses (decisions.md).
- Pieter Daens' questions read: the same pair of versions is asked many times
  ("Saskaaï" 16). Such a pair has one answer everywhere in 947 of 955 cases; as two
  more arbiter inputs the short test gives a small gain (decisions.md). Parked by the
  user at 2026-11-16: not to be built now, to revisit when better models arrive.
- A word's picture against the book's other pictures of it: null, three measures
  (`probe_own_pictures.py`). Its rework is on the checklist.
- The accent on the first vowel of a pair alone ("níet"): on Ex-minnaar the scan's fit
  to the marked drawing less its fit to the plain one finds 38 of 38 with 10 of 7,986
  plain words offered, but that measure's level moves between books (Goede dochter 88
  of 1,500 plain words above the same cut). `robo-first-vowel`
  (`work/runs/first-vowel-plain.sh`, no model) keeps every word's score per drawn form
  in `work/probes/accent-first-vowel/<book>.jsonl` for Ex-minnaar and the tuning books:
  next, a cut set against each book's own plain words of the same vowel pair.
- De kus in de nacht's questions read: 260 of 421 quote questions were ‘m and ‘ns; fixed
  in `quotes.py` (commit a238ea8). The book wants one more build, when the machine is
  free, before its sample is read again.

**The focus the user set today:** the errors that reach the book with no question
("silent errors", the one name now), above all those every reader makes alike; and
short tests before long runs. A reader, prompt or crop is judged by which silent errors
it reads right (`experiments/silent_screen.py`, minutes; AGENTS.md), never by its own
error rate.

**Found today** (decisions.md, 2026-11-15, has every number):
- The read model shown each line's crop at twice its size reads 19 of 97 silent errors
  as printed against 10; olmOCR-2 14, PaddleOCR-VL 1.6 13 (both pulled again by the
  user, on Ollama); all readers together 36. In the build, as extra readers whose
  readings go to the judges as offers (`ROBO_EXTRA_READERS`, off), the enlarged crop
  turned 9 of 11 such errors into a fix or a question, olmOCR 5 of 7, Paddle 3 of 8.
- Offers measured on the scan: stress accents (`accentmarks.py`), a nested quotation's
  outer mark (`quotemarks.py`); a judge of marks alone (`render-mark`). All off.
- Null: trees reading quote marks across books; an accent cut per book; leftover ink
  (twice); the second accent measure as the offers' measure.
- Baidu's Unlimited-OCR-2 (a whole-page model) runs on a patched llama.cpp built apart
  in `~/models/roboscriptorium/llama-unlimited-ocr2/` (the Homebrew one untouched; the
  weights are the blob Ollama pulled, `ollama show --modelfile` names it). One page
  read; to score on whole pages, words and its paragraph and page-number blocks.

**Baselines** (production as of c6088a3): `work/bench/tuning-20261114T233727-389e99a-dirty.json`
and `validation-20261114T233833-82c7529-dirty.json` (their keys now say "silent").

**Running, in order** (screens; each waits for the ones before). Watch with a Monitor
on `work/runs/<name>.out`, re-armed every 30 minutes:
1. `robo-accents-chain` (started 19:37): accent offers: trust data
   `work/probes/ocr-trust-accents/` (resumes per book), arbiter
   `work/models/ocr-trust-accents.pkl`, both benches against the baselines. Taken if
   tuning's silent errors fall and validation doesn't veto.
2. `robo-slot-now-extra-quick` (`work/runs/extra-readers-quick.sh`): the short bench
   (282 pages) with production, then with qwen3.8 at twice the size and olmOCR-2 as
   extra readers, about 5 hours of reading. Says what the extra readers cost on ordinary
   pages. If it holds: a full bench with trust data rebuilt.
3. `robo-accents-mark` (accent offers and the mark judge), then `robo-nested` (nested
   quote offers on top): each a trust-data rebuild, an arbiter and both benches; each
   compared with the run before it.
4. `robo-hints`, `robo-score-init`, `robo-init-ink`, `robo-hyphen-judges`,
   `robo-sorter-panel`: the older tests, last.

**Built, waiting on reading by eye before any review:** De kus in de nacht (814
questions over 610 pages, 421 of them quotes: `work/probes/questions/de-kus-in-de-nacht`),
Pieter Daens (327), Nervous System (72, 35 unanswered).

**For the user's quick confirmation, with crops, once a review is due** (not sent yet):
`work/probes/silent/accents-20261115/`: 9 places where the e-book adds an accent the
print lacks (Goede dochter 8, De vergelding 1) and Au pair's 16 small-capital words the
e-book writes in lower case. Au pair's manifest gets `doubled_singles = true` after the
accent run's benches (checklist).

**Since 02:30** (decisions.md, 2026-11-15): three reworked ideas null (a judge on a band
and a learned referee between the line-role trees; extra signals deciding when to ask);
Pieter Daens' "ofhoe" title mended by hand, then the user: fix `init`, never one book.
The checklist's "Starting from a PDF alone" now holds that plan; what books still need a
person for is measured (`setup_gaps.py`). A hook in `.claude/settings.local.json` puts
the project's purpose and four checks before the agent at every prompt.

**Not taken overnight:** heading places in the arbiter's training; the language model,
the render judge's measures and the book's spacing as arbiter columns; crops cut at the
descenders (off by default).

**Done this session** (decisions.md, 2026-11-14), all on main:
- Both learned trees on the grown slices: not taken, nor the italic trees alone;
  production's trees back and checked.
- Chapter misreads side by side; headings scored as the EPUB sets them.
- The garbled question reads the line as the OCR check settled it (Nervous System's
  unanswered 38 → 35).
- Headings' straight quotes curled (Reis "De gyula’s", Dolittle "MONKEYS’").
- The vocabulary as arbiter columns: still null. The render judge's measures as
  columns: not taken (branch `render-columns`, kept): level on tuning, six more silent
  on validation; the gain lay where the arbiter asks anyway.
- Rule added: a cache version bumped on a branch is one no branch has used.

**Answered by the user (2026-11-14, evening):** Het ijzige land's e-book chapter-number
slip became an erratum kept as printed (`keep = "print"`, the user's idea); the
"cold runs overnight" rule is gone from AGENTS.md (an agent's, never the user's).

**Held back from review:** Nervous System (13 single-reading heading questions, small
capitals in lower case, one garbled line every judge reads right) and Pieter Daens (332
questions, some the machine should settle: "Leopold 11" for II, "°t Is" for ’t). The
checklist has both; the heading questions' evidence is under "One path for every doubt".

**Next:** the text seat's verdict in the morning; then the checklist's order.

**Done on 2026-11-14 (fourth session), the chain `chain-20261114`:** new baselines on
the references without the e-books' stray spaces
(`work/bench/tuning-20261114T094747-bb6bbf8-dirty.json`,
`validation-20261114T094836-37cba55-dirty.json`, since replaced by the baselines with the errata named above); the
second render judge in the first one's place, not taken; the font's kerning chosen per
book, not taken (decisions.md, 2026-11-14). Main's typeface matches are back in
`stages/typeface.json`; the kerned ones are `typeface-kern.json`.

**Answered by the user (2026-11-14):** all 36 places where the e-book departs from its
print: 35 are errata in their books' `errata.toml` (list: `work/probes/silent/
confirm-20261114/errata-pending.json`), each checked to land in a warm build; Au pair's
"want-als" is a speck, the build's error. The user is reporting Vanille's two DBNL slips
to DBNL themselves.

## Render and compare: on by default since 2026-11-13 (the third session, ended 11:10)

**What it is.** The user's idea (2026-11-11): a judge that knows no language. Each
version of a suspect is drawn in the book's typeface and laid over the scan's ink; the
better fit gets the vote (`rendercheck.py`, the judge `render`, fonts in `work/fonts/`).
docs/design.md, "Render and compare", has how it works; decisions.md, 2026-11-11 to 13,
every number.

**Where it stands.** On by default (the user, 2026-11-13: "let's turn it on by default
but also keep working on the weak spots"): `render` in `config.py`'s `alarm_model`;
`work/models/ocr-trust*.pkl` are the `ocr-trust-render3` set and `work/probes/ocr-trust/`
its trust data. The arbiter before: `work/models/ocr-trust-backup-20261113/`, its data
`work/probes/ocr-trust-before-render-20261113/`. Against production before the switch:
tuning BETTER (after review 0.24 → 0.22, questions 3,971 → 3,454, silent 713 → 678),
validation no clear change in words (0.41 → 0.42 [-0.02, +0.03], questions 546 → 486,
silent 272 → 283), worse by the rule on italics 195 → 197.

**Baselines with the vote on by default** (2026-11-13, superseded by those above):
`work/bench/tuning-20261113T090608-fbff45c-dirty.json` and
`validation-20261113T090701-fbff45c-dirty.json`.

**A second render judge beside the first, `render-differ`: not taken** (branch
`render-differ`; decisions.md, 2026-11-13). It compares the two best-fitting versions
only where their drawings differ and is the better judge on every kind (punctuation
93.1% against 90.7%), but as a second vote it moved the bench by a training's noise
(tuning silent 678 → 666, questions 3,453 → 3,485): the two agree on 94–99% of places.

**Nothing runs** (the session ended 2026-11-13, 11:10, at the user's word; every
screen stopped). **Next for the render judge, in this order:**

1. **The second judge in the first one's place** (not beside it: that is what the null
   above asks for). Its training was stopped 80 minutes into about 85 at the session's
   end and lost whole: the script saved only at its end. **That is mended on main**
   (each model is kept in `<path>.training/` as it finishes and a restart goes on from
   them; AGENTS.md, "Every long run can be stopped and picked up"; the checklist's first
   step lists the other runs to check). The worktree's branch doesn't have the mending
   until it is rebased on main: rebase first. Then start it, CPU only, training only
   (it touches no book caches), about 85 minutes:
   `experiments/detached.sh train-differ work/runs/train-differ.sh`, with a watcher;
   it saves `work/models/ocr-trust-differ*.pkl` from `work/probes/ocr-trust-render5/`
   with the worktree `../robo-render`'s code (branch `render-differ`, one commit past
   main as it was at 08:00 on 2026-11-13: rebase it on main first, then check the
   script's `--project ../robo-render` still resolves). Then, once no review is open:

   ```sh
   ROBO_OCR_ASK_BELOW=0.93 ROBO_TRUST_DATA=work/probes/ocr-trust-render5 \
   ROBO_ALARM_MODEL=autotrust-jev:35b-nvfp4,d3:9b,render-differ \
   ROBO_OCR_TRUST_MODEL=work/models/ocr-trust-differ.pkl \
   uv run --project ../robo-render roboscriptorium bench tuning \
     --against work/bench/tuning-20261113T090608-fbff45c-dirty.json
   ```

   and the same for validation against `validation-20261113T090701-fbff45c-dirty.json`
   (through `experiments/timed.sh` in a screen). Taken only if tuning is better than
   the baseline and validation no worse; record it either way.
2. **Books whose typeface the library lacks** (Het laatste bevel, Verminkt: the judge's
   fit on their plain words is 0.79 and 0.83, the tuning books' 0.86–0.97): own-type
   templates, or no vote under a fit the tuning books never reach. A cut by the book's
   fit alone would cost more than it saves (2026-11-14, decisions.md): over 22 books with
   labelled places, fit and the judge's accuracy go together only loosely (r = 0.54);
   Vuurspel, the lowest fit (0.84), is right on 92.4%. Neither book has labelled places,
   so a test on them is a bench.
3. **Font features in the drawing** (Pillow has no libraqm here): real ligatures, small
   capitals and old-style figures for every font, not only Adobe's.

**The user's reviews** (2026-11-13). Hoe wij verdwijnen's spot-check is done: its five
pages are clean in the current build (decisions.md). The 58 confirmations (below,
"Waiting on the user") were handed over at 09:55 with the commands, The Thief-Taker's
Apprentice first; no verdict file had changed by 11:10, so take them as not started.
A review builds its book: run no bench while one is being answered (a server left open after its last answer doesn't count, AGENTS.md, Environment).
Pieter Daens and Nervous System are held back on purpose: rebuild them with the render
judge on and sample their questions first (`experiments/sample_questions.py`), they
should ask fewer.

**The spot-check page** (`experiments/spot_check.py`) now shows scene breaks and flush
openings as the EPUB sets them and greys the words a paragraph has on another page:
the user could not tell either from the old page.

**Done this session, all on main** (decisions.md, 2026-11-12 and 13):

- near-tied typefaces settled by the judge's own fit on plain words (Metro 2033
  72 → 89% of its labelled places); each book's `stages/typeface.json` is the new
  match, the old kept as `typeface-v1.json`;
- book.toml's `typeface`, drafted by `init` with the faces it chose among;
- digits in the font's old-style figures, an ordinal's ending as a superscript;
- the judge's confidence as the probability its pick is the print, from the fit and
  the margin (`experiments/render_confidence.py`);
- no vote on a place set taller than a line of the text (display type);
- a build without a font folder goes on without the judge;
- a heading with a garbled label takes the book's where its number is the one the
  chapter run lacks (`chapters.numbered`);
- the tests need no `work/` (`ROBO_ITALIC_TREES=0` in conftest); a worktree's code
  runs on this checkout's data with `uv run --project ../<worktree>` (AGENTS.md).
- Nulls and not-yets: several faces voting together (no better than one well chosen);
  judging only where two versions' drawings differ (92.6 → 93.3% of places, uneven by
  book: next as arbiter features, for punctuation, the judge's weakest kind).

The night's results, all in decisions.md, 2026-11-13:

- **Main's baselines**, production's arbiter, default settings, with the chapter run
  for titled numbers: `work/bench/tuning-20261113T061845-58a5710-dirty.json` and
  `validation-20261113T061931-58a5710-dirty.json`. Compare later changes with these.
- **The render vote against production on main** (the runs right after those two):
  tuning BETTER (0.24 → 0.22 after review, headings and paragraph breaks level, italics
  1,247 → 1,227), validation WORSE by the rule on italics 195 → 197, words no clear
  change. With a second pair of arbiters (26 books): tuning BETTER, validation NO
  CHANGE.
- **The arbiter trained on Au pair, De vergelding and Glazuur too: not taken again**
  (it asks more and leaves a little less; branch `trust-26`).
- **Chapter numbers before a title run too** ("50 ALEX" → "30 ALEX"), on main.
- A retrained arbiter is compared with production as well as with its control.

**Next for it** (the checklist, "Render and compare", "More tactics"): the
where-they-differ sums as arbiter features; font features in the drawing (Pillow has no
libraqm here: real ligatures, small capitals, old-style figures for every font); books
whose typeface the library lacks (Het laatste bevel, Verminkt: own-type templates).

**How to measure a change to the judge without a bench.** The rebuilt trust data holds
every labelled place: run the judge over a book's rows and count how often its pick is
the print, and how often it has no pick. `experiments/probe_render_compare.py <book>`
does it by kind of error with the probe's own copy of the code; the pipeline's judge is
`rendercheck.Judge.decide` with a suspect's page, box and versions. Read each book's
share, not the total: the total hid 2,800 false votes on 2026-11-12. A change to how a
place is cut or drawn bumps `rendercheck.FITS`, which is in the answers' cache key.

**Left as it is.** The probes' outputs in `work/probes/` (`font-match/`,
`render-compare/`, `face-by-places/`, `render-difference/`, `typeface-v2/`); the
worktree `../robo-render` (branch `render-differ`, the candidate above: keep); the
remote branches `trust-26` (the arbiter on 26 books, not taken) and `chapter-runs`
(merged); two shells of an earlier session still watching a `train-grown5` screen that
is long gone (pids 77861, 77862: harmless, not this session's to kill); four other
worktrees (`../robo-grow6`, `../robo-text`, `../roboscriptorium-caps`,
`../roboscriptorium-py315`), not this session's.

## Running

**Night of 2026-11-11/12.** decisions.md, 2026-11-12, has every number.

**The first session ended for the day on 2026-11-12, about 08:30, at the user's word.**
Nothing of its own runs. Next for it, by the checklist: the nulls that waited for
batch five, trust data for Au pair, De vergelding and Glazuur, the quote check as a
reader; all need the models, free once the second session's run ends.

**Morning of 2026-11-12: four spacing repairs are on main** (chain hyphens beside a
short word, a false paragraph after a dash the layer missed, an ellipsis after a
closing quote, a dash before "’s"; decisions.md, 2026-11-12). Tuning BETTER (38 fixed,
1 made), validation NO CHANGE (7 fixed, none made). The latest runs with the repairs in,
made with the old arbiter at 0.9 (before the switch below):
`work/bench/tuning-20261112T070759-f8e7ab1-dirty.json` and
`validation-20261112T070923-f8e7ab1-dirty.json`. The worktrees `../robo-spacing`
(branch `spacing`, merged) and `../robo-base` (detached, the baseline's checkout) can go.
Left of the spacing step: a dash before a closing quote, which needs the scan
(checklist, "Errors no question asks about").

**Batch five is done**: six books scored whole, NO CHANGE, tuning now 6,180 pages. Its
slices are on main. The trust data of the four grown books that train (Vals alarm, Metro 2033, De
tuin, The Thief-Taker's Apprentice) is rebuilt over their whole books.

**Production's arbiter is switched** (the user, 2026-11-12: "switch to retrained"):
`work/models/ocr-trust*.pkl` are the `ocr-trust-grown5` files (twenty trainings
averaged, a smooth calibration, batch five's trust data), `ocr_ask_below` defaults to
0.93, and the old arbiter is in `work/models/ocr-trust-backup-20261112/`. Not benched
after the copy (the same files were benched under their own name). The next bench on
main is the first with it as the default: it will differ from baselines made with
the old arbiter, so make a fresh baseline first.

**Fresh baselines** (production's arbiter at 0.9, batch five's slices, italics by
place; made from the worktree `../roboscriptorium-caps`, branch `italics-by-place`
rebased on `grow6`): `work/bench/tuning-20261112T021125-7e3d354-dirty.json` and
`validation-20261112T021634-7e3d354-dirty.json`. The twenty seeds at 0.93 against them:
`tuning-20261112T021546-7e3d354-dirty.json`, `validation-20261112T021713-7e3d354-dirty.json`.

**Batch five's slices and the italic count by place are on main** (2026-11-12 06:15);
the worktrees `../robo-grow6` and `../roboscriptorium-caps` hold merged branches and
can go.

**Done for the night's last step** (the silent errors that look like the reference's):
223 places read on their crops, 58 for the user to confirm (below, "Waiting on the
user"), 75 the build's, now steps in the checklist ("Errors no question asks about").

The quote reader with its kept question is still not taken (16 asked places silent on
tuning, not read place by place; next: trust data with the two quote readers and the
arbiter retrained on them).

Found at ~06:00: retraining is exact (the arbiter trained again on
production's trust data is production's file byte for byte), and the control's 15 more
silent errors came from 72 suspects of 30,647 whose versions differ. So one retrained
arbiter against another is noise at that size: bring the arbiter's variance down
(seeds or bags averaged) before weighing the next retraining, batch five's included.

**Small capitals: the lower-case doubts are on by default** (`ROBO_LOWER_CAPITALS`, the
user's call on 2026-11-11: about 1.7% more questions; on tuning silent errors
524 → 512, none made silent; validation nine more questions, no place changed), on
main, and the day's baseline has them. The checklist section "Small capitals" lists
what is left. The night's trust data and arbiters (`work/probes/ocr-trust-{caps,ctl}`,
`work/models/ocr-trust-{caps,ctl,rep}*.pkl`) are not in use.

**The quote check as a reader: benched twice, not taken** (`ROBO_QUOTE_READER=1`, off).
Both fixes are on main (6b57830: a last line another reading already ends paired takes
that reading's end; De tuin's fixes 2,143 → 2,155 against 2,156 off, OCR questions
111 → 98 against 83, quote lines 146 → 80; 023e983: only where that leaves the
paragraph fewer unpaired marks, The Loudest Sound and Nothing's "one.”’"). Still asked by the quote check itself: a mark opening a word
("’bout", 40 lines in The Loudest Sound and Nothing).

**The user is reviewing Nervous System** (started 2026-11-10 ~06:40, answers in
`work/nervous-system/review/regions.jsonl`). Their first card, PDF 13, was "a mess": fixed
in 47ecbef (washed-out cards read only inked lines; no repeating readings). A review server
started before that commit shows the old cards: restart it (answers are kept). Then Going
into a Dark House and The Loudest Sound and Nothing (checklist, the user's books).

**Done the night of 2026-11-09/10** (decisions.md has the numbers): Nervous System built and
checked (epubcheck clean; 70 questions after the fixes, sampled; waits on the user's
review); the judges asked one at a time over the book (judging ~10× faster: 585 model
reloads an hour had eaten it); the text layer's cache now hits; the arbiter scores a book
in one call; `init` keeps a page under the running head past the end and starts after the
title page; a table on a text page (a library label) is asked; no lost-initial questions
where a book opens sections in capitals. Nulls: the page-kind model told its neighbours'
kinds; washed-out pages asked their kind (it called faint print blank); the second scan as
a witness (two errors in 756 places on Nervous System).

**Next for these books:** when each build ends, check its ends, story-title headings and
library label (The Loudest Sound and Nothing has Blackpool's on PDF 7), sample its questions
(`experiments/sample_questions.py`), and list them for the user's review. Not yet built:
glm-ocr and tesseract beside Qwen (~10–14 min a cold book, the code review's item); a
cold bench must stay one book at a time (`ROBO_BENCH_WORKERS=1`), or the judges of
parallel books evict each other.

**No heavy work during the user's working day** (the user, 2026-11-09: "the memory
pressure is too great. can we hold off on the heavy work until i get done with my
dayjob?"): builds, benches, probes with models and batch five wait until they say
they're done. Light work only meanwhile (docs, analysis of results on disk, code checked
by unit tests).

**How to work with the user** (2026-11-09, memory `no-foreground-waits`): never wait on a
run in the foreground. Start it detached with its watcher, say so, and end the turn. Keep
turns short and report each result as it comes: "going incommunicative for an hour is not
polite."

## Next, in order, once the user frees the machine

1. **The quote reader's benches**, then the small-capitals default once the user answers
   (Running, above).
2. **Batch five** (the user said go, 2026-11-09): `work/runs/grow6.patch`, Vals alarm, Metro,
   De tuin, Thief-Taker, Au pair and De vergelding scored whole, ~915 pages, ~14 h cold.
   Overnight. Before its arbiter is retrained, read the reproduction's result (Running,
   above): a plain retraining was worse than production's arbiter. Then retest pass 4 (branch `text-seat`,
   worktree `../robo-text`, arbiter `work/models/ocr-trust-p4*.pkl`, data
   `work/probes/ocr-trust-p4/`) and the vocabulary feature on the grown trust data.
3. Hints for the new judges (which kinds of OCR error to look for, tried only with clef),
   then d3 and autotrust-jev as the line-end hyphen judge; then the whole-page readers
   retested as line readers.

## Production

Since 2026-11-09 (decisions.md): autotrust-jev 35B and d3 9B beside clef, asking below
0.9; the arbiter before kept as `work/models/ocr-trust-p0*.pkl` and
`work/probes/ocr-trust-p0/`. Merged that night: the hyphen rules, pages too poor to read,
heading capitals by the book's run (tuning BETTER, 72 words fixed, none made). Not taken:
pass 4 (validation's silent places 170 → 178), Mistral-Small 3.2 as a text judge.

## Done 2026-11-06 evening

- **Qwen3.8-Flash-Next UD-Q2_K_XL rejected** as reader and witness (models.md, decisions.md):
  on the quiet set's lines every reader gets wrong, 0 of 5 plain, 4 of 23 with the crop
  doubled (two real), 2 of 12 thinking; it swaps real words; ~15 s a line from the SSD.
- **Taken: a Dutch line-end break between clashing vowels keeps its hyphen**
  (`hyphens.vowel_clash`): tuning 3 fixed, validation 1, none made.
- **Taken, every one benched warm, validation no change on each, no heading of the
  user's four books changed** (decisions.md has the numbers): tuning heading errors
  32 → 22, silent wrong words 839 → 755:
  - a misread chapter number where the run has a gap read again by glm-ocr
    (`chapters.run_gaps`, `stages/run-gaps.json`): Monterosso 22 of 22;
  - a display line under a heading on a page without running text is part of it
    (`title_lines`, "part-page"): Het geluid van bananen's "Stof", "Jullie", "Wij";
  - a number heading off the run and off the middle is a speck (`chapters.off_run`):
    Doodskleed's "7" and "3";
  - punctuation after a chapter number left out of its value: Thief-Taker's "20 ;";
  - a text block the layer lost whole cut into lines by its ink and read
    (`missing.blocks`): Dolittle's PDF 97, 105 wrong words fixed (81 silent);
  - the scorer folds subscript digits and the fraction slash (Artemis's "CO₂").
- **Not taken**: a run-on heading measured against the book's full line
  (`work/runs/book-full.patch`): no longer needed once the lost block is read.
- **Lesson**: never edit `src/` while a bench runs; its validation half loads the edit.
- **`experiments/heading_misses.py`** lists each book's missing and extra headings.
- **`doctor` runs again** (4dba7ae, broken since 2026-10-24, now tested).
- **Tests never reach the machine's Ollama** (5afd2b5): `ROBO_OLLAMA_URL` on a closed port in
  every test; one pipeline test had passed only because qwen answered it.

## Done 2026-11-05 evening to 11-06 morning (decisions.md has every number)

- **Taken, all benched, none made an error of its own**:
  - a full stop added mid-line before an undisputed lower-case word, and an "ij" read as
    u, ui, y, ii or i, no versions (`ocrcheck.line_end_stop`, `ij_misread`; 17f5504):
    tuning 5 fixed, validation 5;
  - lines of dots ("‘...’", a silent reply) read from inked slots between layer lines,
    kept as body past the line-role trees, with the quote marks their ink shows
    (`missing.slots`, `slot_lines`, `quoted`), and a quote mark misread from a speck no
    version (`ocrcheck.quote_misread`; 367085c): tuning 8 fixed, validation 5;
  - whole lines of text the layer lost, read from the same slots where as long as a line
    of the page (`missing._fills`; 82c1b39): tuning 103 wrong words fixed (12 silent,
    most were lost-line questions the reviewer had to type), validation 9.
- **Lessons**: dropping one of two sibling readings strengthens the other in the arbiter's
  eyes (a rule must drop a misread in all its spellings); the line-role trees take any
  line with no letter for a speck; a slot narrowed to its ink needs its length judged
  against a whole line too.
- **Nulls**: the build's 18 accent errors are accent-shaped specks (as 2026-10-26 found);
  a single quote for a double isn't told by the book's quote style; a comma added after a
  word is wrong 13 of 14, no rule.
- **Set review** (87c7dfe): Dolittle past the layer-CER line since scored whole, its errors
  the pipeline's, kept. Primer errors chart regenerated (0f1a9aa).

## Next, for the agent

1. The open steps of docs/checklist.md in its order. The silent errors left on tuning
   (585 places): stress accents 105 (half the reference's), compound hyphens 86 (line-end
   breaks, 57 a hyphen lost), letters 76, punctuation 59. Extra text's 969 words are
   mostly Afscheid's washed-out pages, asked by design.
2. Idle machine time grows the slices (checklist).

## Waiting on the user

- **58 silent errors that look like the e-book's, to confirm** (~15 min; decisions.md,
  2026-11-12). In each the agent read the print as ours has it; the answer is still the
  user's:

  ```sh
  # 11 places
  uv run roboscriptorium review work/the-thief-takers-apprentice--ia-scan --only work/probes/silent/candidates-20261112.json
  # 8 places
  uv run roboscriptorium review work/de-stilte-van-de-hel--ia-scan --pages 11-101 --chapters 1-15 --only work/probes/silent/candidates-20261112.json
  # 8 places
  uv run roboscriptorium review work/metro-2033--ia-scan --only work/probes/silent/candidates-20261112.json
  # 7 places
  uv run roboscriptorium review work/de-geruchten--ia-scan --pages 9-97 --chapters 2-22 --only work/probes/silent/candidates-20261112.json
  # 3 places
  uv run roboscriptorium review work/afscheid-van-verspilde-tijd--ia-scan --only work/probes/silent/candidates-20261112.json
  # 3 places
  uv run roboscriptorium review work/het-ijzige-land--ia-scan --only work/probes/silent/candidates-20261112.json
  # 3 places
  uv run roboscriptorium review work/verminkt--ia-scan --pages 7-100 --only work/probes/silent/candidates-20261112.json
  # 2 places
  uv run roboscriptorium review work/vanille-en-andere-smaken--dbnl-scan --pages 9-79 --chapters 1-16 --only work/probes/silent/candidates-20261112.json
  # 2 places
  uv run roboscriptorium review work/vuurspel--ia-scan --pages 9-111 --chapters 1-6 --only work/probes/silent/candidates-20261112.json
  # 2 places
  uv run roboscriptorium review work/de-vergelding--ia-scan --only work/probes/silent/candidates-20261112.json
  # 2 places
  uv run roboscriptorium review work/het-laatste-bevel--ia-scan --pages 9-100 --chapters 1-5 --only work/probes/silent/candidates-20261112.json
  # 1 places
  uv run roboscriptorium review work/artemis--ia-scan --only work/probes/silent/candidates-20261112.json
  # 1 places
  uv run roboscriptorium review work/au-pair--ia-scan --only work/probes/silent/candidates-20261112.json
  # 1 places
  uv run roboscriptorium review work/het-heft-in-eigen-hand--ia-scan --only work/probes/silent/candidates-20261112.json
  # 1 places
  uv run roboscriptorium review work/normal-people--ia-scan --pages 146-232 --chapters 23-31 --only work/probes/silent/candidates-20261112.json
  # 1 places
  uv run roboscriptorium review work/monterosso-mon-amour--ia-scan --only work/probes/silent/candidates-20261112.json
  # 1 places
  uv run roboscriptorium review work/reis-om-mijn-schedel--ia-scan --only work/probes/silent/candidates-20261112.json
  # 1 places
  uv run roboscriptorium review work/goede-dochter--ia-scan --only work/probes/silent/candidates-20261112.json
  ```
- Hoe wij verdwijnen's spot-check is done (2026-11-13: nothing wrong on its five pages
  but the two italics fixed since). Its read-through waits on the user's word (no full
  read-throughs soon).
- Pieter Daens' **review**: 292 questions, `uv run roboscriptorium review work/pieter-daens`.
- A read book's rebuild that changes text goes to the user by eye, every difference
  (the user, 2026-11-04): `experiments/rebuild_diff.py <book> <old.epub> [notes.json]`.

## Done 2026-11-03 evening and 11-04 morning (decisions.md has every number)

- **Not taken**: a lone word with a diagonal letter or acute accent held to 12° (tuning
  italic errors 2,445 → 2,588): a capital Z or W leans the whole word ~26°, past any cut.
- **Built: the learned italic decision** (`italics.Trees`): trained on the golden pairs'
  aligned words. Lesson: counts of measured words let the trees memorise single pages of
  other books; without them, and with each book weighing alike, the trees generalise.
- **Built: chapter labels** (`chapters.title_lines`): Het schaduwhuis' narrator names.

## Done 2026-11-01 and 02 (decisions.md has every number)

- **Two new books of the user's, timed end to end** (README, docs/run-times.md): Hoe wij
  verdwijnen 4 h 14 min (300 pages), Pieter Daens 12 h 22 min (804).
- **What reading them showed, now the pipeline's own** (AGENTS.md rule, "What an agent
  finds by eye"): chapter numbers by their run (`chapters.py`); short pages, pages before
  the first heading and listing pages asked the page-kind question (mottos, dedications,
  tables of contents; blank pages left out only when washed out); title-page subtitles;
  a motto's wrapped lines joined; italics uniform in a motto; glm-ocr's talk on specks no
  line; `init` walking inward past the edge (Daens' ads); a structure check and a
  comparison with the last build printed by every `build`; heading errors in the bench's
  verdict; the review's obvious questions out.
- Benches: the 11-01 batch, heading errors 102 → 82 on tuning, 50 → 45 validation; the
  11-02 batch on the grown slices, after review 0.34 → 0.33, heading errors 104 → 72,
  missing text 0.073 → 0.048, validation no change; the dash fix, dash errors to zero.
- Also taken: quotes closed at a paragraph's end where the reading adds only the mark
  (39/39 on tuning); possessives after a sibilant ("Maurice’ moeder") no quote; the
  bench names a book whose silent errors double (`bench.doubled`); bench in parallel.

## Done 2026-10-25 and 26 (decisions.md has every number)

- **Slices grown twice** (the user: idle machine time may go to it): seven slices on the 25th
  (~585 pages), eleven more on the 26th (~860 pages, 13 h cold). On the pages both runs
  share: no change. Tuning went from ~1,700 to ~3,100 pages, and the after-review interval
  should narrow from ±0.010 to about ±0.008.
- **Not taken**: the arbiter retrained on the grown slices (more silent errors; the second time
  more rows haven't helped, so the arbiter needs a new signal, not more data); page roles on
  the grown slices, and withheld on picture pages (no change; the harm is in the line-role
  trees trained with page features).
- **Au pair's 13 small capitals** settled by the user's verdicts (0.286 → 0.277 on the slices
  of the 25th). Lesson: check scan crops before asking; bring a verdict only when it needs a
  human's eye, with crops beside a confident reading.
- **Lessons**: compare against a run made after the latest verdicts; a slice's growth can move
  its old pages a little (the book's own spellings and abbreviations come from all its pages);
  the cold rate is about 0.9 min a page.

## Done 2026-10-24 (decisions.md has every number)

- **Taken**:
  - a full stop for a line's last comma before a lower-case line is no version
    (`ocrcheck.stop_for_comma`: 6 silent words fixed, none made);
  - readings that accent one letter of a doubled a, o or u, or carry `~ ^ |`, are no version
    (`half_accent`, `garbled`: no change on the bench, never right in the trust data);
  - any short line in justified text ends a paragraph (`reflow._short_end`: salutations and
    datelines before a letter's flush body; breaks 0.057 → 0.045 on tuning,
    0.202 → 0.196 on validation, words unchanged);
  - an image-only scan's dash style measured on the image (`scanstyle.guess` through the first
    reading's words; Vanille's typography 0.56 → 0.00 a page).
- **Not taken**:
  - a sureness threshold per kind of question;
  - Qwen's token probabilities, image-gain included, as a silent-error signal;
  - Qwen as the line-end hyphen judge;
  - Kraken as a witness;
  - Qwen's page roles for the trees, unmarked (more wrong words) and with the lines inside
    pictures marked (half the harm, still no change; code kept, off);
  - the comma rule mid-line (1 fixed, 1 made: an author's stop before a lower-case
    quotation);
  - Winnow subtracted (worse, 0.282 → 0.316: it stays);
  - Qwen for `init`'s page kinds (no better than clef-flash, more ends cut).
- **Screened**: LightOnOCR-3 1B and 4B as line readers, unfit, weaker than olmOCR-2 (the 1B's
  checkpoint needs its weights renamed, a bare crop needs a white margin;
  `experiments/lighton_read.py`).
- **New instruments**:
  - the quiet set (`experiments/quiet_set.py`, 423 frozen lines where the layer, glm-ocr
    and qwen agree): they are wrong together on only 23 lines of the tuning slices, so a
    new line witness can add a handful;
  - `experiments/witness_score.py` for the reader set.
- **Measured**:
  - the trust data's `choice` is the fixed rule's, not the arbiter's: join to a build's
    `ocr-check.json` for the arbiter's;
  - books set flush put no extra lead between paragraphs;
  - `bench quick` ranks a change that acts everywhere as tuning does, with a fifth of the
    power, and never sees front matter or picture pages;
  - batching identical questions would save 7% of cards;
  - an accent told from an i-dot by shape alone: AUC 0.66–0.76, too weak (the per-book
    alphabet parked);
  - ABBYY's letter confidence: private on every lent scan, dropped.
- **Sets reviewed**: no pair past the thresholds, nothing retired.
- **Stella**: rebuilt with all of the above, text and paragraphs unchanged.

## Next, in order

1. **The arbiter's own silent errors: probed 2026-10-26, nothing taken.** They are what its
   0.8 sureness line costs (9–11 questions for each one caught past it), plus De vergelding's
   page budget (three questions a page caught 8 silent words there, tuning no change). The
   accent half goes both ways (specks read as accents in Doodskleed, Glazuur, Monterosso;
   emphasis dropped in Goede dochter, Het schaduwhuis, Au pair), and the ink's shape over the
   letter adds nothing to the trees. Left: De vergelding's own arbiter (it has the most
   unsure suspects, never trained on); a speck classifier with more labelled pages.
2. **Compound hyphens at line ends** (25 silent with no suspect): no cue found in qwen, clef
   or the obvious signals; only a learner with a new feature can reach them.
3. **Emphasis accents and the dotless ı** (the quiet set's largest classes after small
   capitals): they need each mark tied to its letter, which the layer's letter boxes can't give.
   A reader that gives letter positions is the way in.
4. **Verse and lists** (Dolittle's poem, Thief-Taker's song, Glazuur's numbered list): most of
   the paragraph errors left on tuning; in scope later, per AGENTS.md.
5. **Qwen faster on the same output**: measured 2026-10-24, a line read is half prefill and a
   quarter decode, so speculative decoding buys little; fewer image reads (whole pages) is the lever.
6. **Page roles need the line-role trees retrained** with picture pages and mottos labelled
   (Dolittle's picture-page lines go wrong under the trees trained with page features, whatever
   qwen says); only then bench page roles again.
7. **The slices are grown as far as the listed room goes** (batch five, 2026-11-12).

## When a new vision model appears

Gate for a candidate that fits 64 GB, in order:
1. the quiet set: can it read any of the 23 lines every reader gets wrong? A few minutes;
   a slow candidate stops after its first 25 lines unless they show a gain;
2. `experiments/screen_reader.sh <label> <model dir or ollama name>` (the reader set, then
   the vote simulation);
3. `probe_accent_readers.py`;
4. only then a trust-data rebuild and a bench.

Ask before a download over 1 GB. A model outside Ollama gets its own environment in
`~/models/roboscriptorium/` (as `lighton-env`).

## Waiting on the user

- **A flush-set book for tuning** (golden-notes.md, gaps): a scan and the publisher's EPUB of
  a book printed without paragraph indents, not A.W. Bruna's. Every break error left in the
  flush books is a start after a full line, which only a learned model finds, and without a
  flush tuning book no such change can be chosen.
- **Specks** (parked): the speck classifier needs labelled pages from more scans.
- **Disk**: `work/models/mlx-env` (809 MB) and `~/models/roboscriptorium/lighton-env` (767 MB, the
  LightOnOCR runtime; its weights were deleted 2026-10-24, the user agreeing) stay until the user
  says they can go. `work/models/ocr-trust-grown*.pkl` (the arbiter retrained on the
  25th, not taken) can go too.
- Andere levens: seven candidate misprints saved as printed
  (`work/probes/carrere-editions/andere-levens-checked.md`); the user says which, if any, are
  misprints.

## Standing notes

- **Een Russische roman is on hold** (the user, 2026-10-19) until three washed-out pages
  (46, 47, 259) are photographed from a library copy: no builds, reviews or probes on it.
- **No full read-throughs of any book soon** (the user, 2026-10-20) beyond Stella's.
- `experiments/screen_reader.sh <label>` treats the label as an Ollama model; for a readings
  file label run `tryout.py`'s reading step and `vote_sim.py <stem>` directly.
- A Monitor watcher expires after 30 minutes whatever its timeout: re-arm it on a long run.

## How to run things

- Long runs through `experiments/timed.sh` inside `experiments/detached.sh` (a screen), each
  with a watcher. Warm benches take about 11 minutes (tuning) and 5 (validation); `bench
  quick` 6.
- A bench of a change: run it, then compare against the baseline by path:
  `bench tuning --against work/bench/<run>.json`, `bench-diff <old.json> <new.json>` place by
  place, and `bench.verdict(old, new)` in Python for the paired interval. A change of
  settings only (an environment variable) needs no worktree; a code change's "before" is the
  baseline run.
- Check every writer of what you change: the scored text is built from `corrections.apply`,
  the question view from `ocrcheck.apply`.
- Stopping a run: `experiments/stop-run.sh <name>`; a job waiting on another's screen starts
  the moment that screen goes, so stop the waiters first.

## Recovery, 2026-10-11: an agent destroyed work/

Restored from the user's Downloads and the 2026-10-07 backup (details in
docs/decisions.md, 2026-10-11). Never symlink `work` into a worktree; stage files by name.
