# AGENTS.md — Roboscriptorium

Instructions for any coding agent (and human) working in this repo. Read it before
starting; keep it true. It holds the rules, the scope and the map; the detail lives in
the documents it names, each with one job.

## Core principles

What lasts (the user, 2026-10-18): the models' reading and judging will keep getting
better, and code will keep getting cheaper to write and maintain; these principles are
what the project is. Everything below them is today's way of meeting them.

1. **The print, faithfully.** Exact words, spelling, paragraphs and the book's own
   typography; no house style; fix only clear reading errors, never the author.
2. **Build the machine, not the book.** Readers and judges that fail differently,
   combined by learned trust, the reviewer's answers as its labels; every job keeps a
   labelled set, so a new model is benchmarked and plugged in where it wins. A book
   comes out right because the machine does.
3. **Learned, not hand-written** (the user, 2026-10-13). A decision is learned from
   labels (the golden books, the reviewer's answers) wherever it can be; a rule is
   replaced once the bench says the learned decision is at least as good. What is true
   by definition (a chapter heading appears once, an apostrophe is `’`) may stay code.
4. **The faithful golden pair is the arbiter.** A scan and the publisher's own text of
   that printing: the build must turn the one into the other. Every change is judged on
   them, paired, before and after; a human verdict mends a reference only where it
   departs from its print. How faithful each is: docs/golden-books.md, Faithfulness.
5. **The reader's time is the scarcest resource.** Ask only what the machine can't
   settle, and only once the machine has done all it can.
6. **Nothing is "the way we do it".** Every block keeps its place only while the
   evidence says it earns it; reorder, add or remove when it serves the outcome.
7. **Record what was learned.** Every result, null ones too, with its numbers and its
   reason, so it never has to be found again.

## The documents

Each fact lives in one file; the others point to it. A change updates the file that
owns the fact in the same commit.

| File | Job | When it changes |
| --- | --- | --- |
| `AGENTS.md` | rules, scope, conventions, the map | a rule, tool or convention changes |
| `HANDOVER.md` | the state of play: what runs, what's next, what waits on the user | rewritten at the end of every session |
| [docs/checklist.md](docs/checklist.md) | the plan: every open step in order, who does it, how long; below it what's done, one line each | the same change that plans, ticks or drops a step |
| [docs/outlook.md](docs/outlook.md) | how close the build is, where results can still move, what was tried without effect | the bench moves, or a probe comes back null |
| [docs/decisions.md](docs/decisions.md) | the dated log: what was learned or decided, with the numbers | every change that teaches something |
| [docs/design.md](docs/design.md) | why each component is there: what it catches, its failure, the measurement | a component or the evidence for it changes |
| [docs/optimism.md](docs/optimism.md) | how likely the goal looks, dated, as the user asks it | the user asks, or a result moves it (a first look, a bench of a new idea) |
| [docs/run-times.md](docs/run-times.md) | wall-clock minutes of long runs, appended by `experiments/timed.sh` | each timed run |
| [docs/modules.md](docs/modules.md) | the code, module by module | a module changes |
| [docs/models.md](docs/models.md) | every model tried, by role, with its verdict; how the ones in use are set up | a model is screened or set up |
| [docs/golden-notes.md](docs/golden-notes.md) | working with golden pairs (fetch, derive, check a candidate, deviations, verdicts, retiring, set reviews); each golden pair: edition, what makes it hard, known deviations, what it is for; the gaps to hunt for; the manifest keys that undo deviations | a pair is added, sliced or retired; a key is added; a set review |
| [docs/golden-books.md](docs/golden-books.md) | the pairs' numbers, **generated** by `experiments/golden_overview.py` | regenerated after a pair changes |
| [docs/hosted-inference.md](docs/hosted-inference.md) | the plan for a window of free hosted inference: what to learn, what carries back, the guardrails | access comes, or a hosted run teaches something |
| [docs/primer.md](docs/primer.md) | for a person new or returning: the problem from first principles, how a change is judged, where the gains are expected, the vocabulary | the approach, the bets or the vocabulary change; its errors chart regenerated (`experiments/primer_errors.py`) after a bench that moves the errors, its render-and-compare figure (`experiments/primer_render_figure.py`) when that judge's drawing or fit changes, its `.d2` diagrams rendered again when edited |
| [docs/README.md](docs/README.md) | the map of docs/ for people: what each file tells, which to read and which only to look things up in (GitHub shows it under the folder's list) | a file in docs/ is added, removed or changes its job |
| `README.md` | the first entry, for people: what it makes, the idea in brief, today's result, how to run it, where to read more | the approach, the result, the models to pull or the commands change |
| [docs/how-it-works.md](docs/how-it-works.md), `docs/pipeline.d2` | for people: how a build runs, stage by stage | the stages, their order or their models change |

Cite a step or a section by its words, never by its number: numbers are positions and
get renumbered. Don't add a file to this table without a job no other file has.

## Standing rules

### The record

- **Keep the docs true yourself.** When something is learned or decided, update the file
  that owns it in the same change and add a dated line to docs/decisions.md, unasked.
- **Write down why.** Every component's job and the evidence that it earns it live in
  docs/design.md; a component without one gets it before the change that touches it.
- **Keep the diagram true.** A change to the stages, their order or a stage's model
  updates `docs/how-it-works.md` and `docs/pipeline.d2` (and `README.md` if the models to
  pull change); render with `d2 docs/pipeline.d2 docs/pipeline.svg` and commit both.
- **Read `HANDOVER.md` at the start of a session** and rewrite it at the end. Choose work
  from docs/checklist.md (the order) and docs/outlook.md (the room left).
- **This file is the single source of agent instructions**: no `CLAUDE.md`.
- **Code is disposable; the labels and the record aren't** (the user, 2026-10-18). A
  later model can't regenerate the human labels (review answers, verdicts, errata in
  `work/`), the golden pairs with their provenance, or the record of what was tried and
  why. Spend effort where it adds to these.

### Git, data and installs

- **Git:** signed commits straight to `main`, pushed whenever convenient; no PRs. Lint
  and tests before every commit that touches code or tests; a commit of docs and
  diagrams alone needs neither (the tests take minutes and check none of it).
- **No copyrighted material in git.** Books, page images, OCR output and golden pages
  live in `work/` (gitignored). Commit only code, prompts, question sets, configs and
  synthetic fixtures.
- **`work/` holds what git doesn't** (books, caches, review answers, the verdicts on
  every golden book in copyright). Point at it by path; stage files by name. A
  worktree's code runs on the main checkout's data: `uv run --project ../<worktree>
  python …` there; its tests need no `work/`. Give such a run its own output folder
  under `work/probes/` when a run in flight reads the stage caches it would rewrite.
  What will be needed again goes under `work/` (`work/probes/`, source EPUBs in
  `work/.cache/{gutenberg,publisher}/`), never in a session scratchpad.
- **Local first.** AI runs on this machine via Ollama. A hosted model
  (`clients/openrouter.py`) costs money and sends copyrighted page crops away: it is
  used **only when the user explicitly allows it, for that use**, each permission for
  one run, and stays out of `config.py`'s defaults. Then: pinned to one provider and
  precision, no fallback, no provider that keeps prompts, measured against the local
  model first. With free hosted inference on offer, read
  [docs/hosted-inference.md](docs/hosted-inference.md) before planning its use.
- **Installs:** Homebrew tools, Python deps and Ollama models freely; the user pulls
  large model downloads. Record each under [Environment](#environment), a model's setup
  in docs/models.md (Setup).

### The user's time

- **The user's work comes first** (the user, 2026-11-14: "you stop your work and give
  priority to mine"). A `build` or a review's build the user starts pauses the agent's
  `robo-*` screens while it runs (`priority.first`). Before handing the user a command,
  check what it costs them (when the book was last built, what it will ask the models)
  and clear or warm the machine for it.
- **The user's review comes last** (the user, 2026-10-16). Before sending them to
  review or read a book, finish every checklist step that would change its text or
  questions.
- **Handholding first.** Flag uncertain output for review over guessing silently;
  automation grows only as measured quality earns it.
- **What an agent finds by eye, the machine learns to find** (the user, 2026-11-01). An
  error seen in a built book becomes, in the same change, a repair in the pipeline, a
  check every build runs, or a case the bench scores; one book alone is never the fix.
- **A problem goes to the user as a proposal, open to a better idea** (the user,
  2026-11-14): the situation in clear English, what solving it gains, what leaving it
  costs; a solution of your own, the rules as written included in what may change; then
  ask whether they have a better one.
- **Questions the bench can't weigh** (the reviewer's time against wrong words) are the
  user's call: ask in one short sentence.

### Runs

- **Quality over speed.** Take the more accurate method even when several times slower;
  cache slow stages per book and run long builds in the background.
- **Time long runs and give an estimate first.** Anything over a few minutes runs
  through `experiments/timed.sh` (label, pages, log file, command), which appends to
  docs/run-times.md; say beforehand how long it should take from that table. Start it
  with `experiments/detached.sh <name> <command…>` (a `screen` session, output in
  `work/runs/<name>.out`); stop it with `experiments/stop-run.sh <name>` (quitting the
  screen leaves its command running).
- **Every background or screen job has a watcher** (the user, 2026-10-17), started in
  the same turn: one that wakes the agent on each step, error and end (the Monitor
  tool, re-armed when it expires). In a script `screen -ls` exits 1 when sessions
  exist: test it as `{ screen -ls || true; } | grep -q …`.
- **Check every input before queuing a run, every item.** Without models: everything
  the run reads exists for every book it will touch (scan, caches, models pulled), and
  books retired since a set was made are out. A test on one book tests that book only.
- **Before a run is queued, two answers are written into its script**, and
  `experiments/detached.sh` refuses a script without them (the user, 2026-11-16: "you
  should be robust in your operations to withstand interruption and pick up quickly";
  a bench reloaded a judge at every question and could not be stopped without losing
  eight books' answers). `# resumes:` what it keeps as it goes and what a stop loses,
  found by reading the code that calls the models, down to where it writes its cache:
  if a stop loses more than a few minutes, mend the code first. `# models:` the Ollama
  models it asks; past 48 GB together, `# one at a time:` how it keeps them from
  swapping (one model over all its questions, then the next; one book at a time).
  New code that calls a model saves each answer as it comes and groups its calls by
  model, and its test stops it midway and starts it again.
- **Every long run can be stopped and picked up** (the user, 2026-11-13: "make anything
  resumable … time is rare and valuable"). It keeps each finished piece (a model, a
  book, a page) and resumes from them; one that saves only at its end is a bug to fix
  before its next use. Before stopping a run, even when told to, say how far it is
  against how long its like took (docs/run-times.md) and whether it resumes.
- **A probe beside a running chain sends the chain's model options** (no `num_ctx` of
  its own): Ollama reloads a model whenever the requested context differs.
- **Never idle while the checklist has open steps** (the user, 2026-10-24: "as long as
  you can see todos, you're not to be idle"). After a task, a report or a question, start
  the next open step in the same turn; say what is next and start it. A question blocks
  only its own step; a run in flight blocks only other model jobs. Stop only when every
  open step waits on the user, and say which.
- **An idea waiting for model time goes into the queue at once** (the user, 2026-11-15):
  written, checked without models (`--dry`) and queued behind the runs in flight in the
  same turn.

### Experiments and ideas

- **At every result, question the structure** (principle 6; the user, 2026-10-17: "i
  just don't want ever see you get complascent"): which block a probe, bench or review
  batch makes redundant, which it suggests, which order it questions; when something
  new works, what it lets us remove. Proposing these experiments is the agent's job.
- **Test the architecture, not only its settings** (the user, 2026-10-13: "fine tuning
  has diminishing returns"). Before saying a model can't do something, or parking an
  idea, try it on a few golden pages: a model reading a whole page, a model doing a
  stage's job, a stage left out. The checklist keeps the list ("Assumptions to test").
- **Cheap experiments run unasked:** A/B a prompt, a crop or a setting on a frozen set;
  record null results too. Anything over a few minutes, or costing the user time or
  money, is explained first: why, what it should teach, how long.
- **The shortest test that answers the question** (the user, 2026-10-15): the pages a
  change touches, in minutes. The full bench guards against regressions elsewhere: once
  a change has passed its short test, several changes batched.
- **Decide upstream changes on the frozen sets; the bench confirms.** A change upstream
  of the stage caches (a prompt, a crop, a model, the arbiter) makes a bench run cold
  for hours: choose on `experiments/tryout.py` in minutes, bench the winner once.
- **A null is a null for its models** (the user, 2026-11-08). Record with every null
  which component it failed on. When that component changes (a model screened in, a new
  panel, a retrained arbiter), go through the nulls it blocked (docs/outlook.md, "Tried,
  and why it didn't help") and retest the cheap ones.
- **Rework an idea before dropping it** (the user, 2026-11-15: "i fear we might dismiss
  good ideas after the first version of them doesn't pan out"). Beside the null, write
  its reason and the versions that would dodge it (another place in the pipeline, a
  narrower scope, another signal, combined with another idea); try the most promising.

## Engineering practices

Each rule names the mistake it prevents; check a change against them before committing.

- **A stage returns new data; it never edits its input.** A function that must change
  pages returns changed copies.
- **Say which version of the data a consumer gets** (raw text layer or corrected copy,
  model roles or answered roles) in the type, field or docstring. A key, cache entry or
  line reference comes from the version it identifies.
- **Positions aren't identities.** Carry the original identity (`Line.source`) through
  any stage that inserts or removes lines.
- **Before finishing, find every reader of what you changed**: grep the consumers of a
  function, field or file and check each still gets what it expects.
- **Test the seams.** A new stage, or a change in what flows between stages, gets a test
  through `pipeline.run` (`tests/test_pipeline.py`).
- **A rule that changes the author's text needs its counterexamples tested**, written
  before the cases where it must fire; where the two can't be told apart, flag for
  review.
- **Measure with `roboscriptorium bench`, before and after**, on every golden book
  (docs/design.md, Measuring): only its paired comparison says whether a change is
  real. Choose on `bench tuning`; `bench validation` only vetoes (the user,
  2026-10-17): a choice made on validation scores makes them tuning. So validation
  runs only once tuning shows a gain, read against its control where the change retrains
  anything: a null on tuning ends the test, with nothing for validation to veto (the
  user, 2026-11-20: "if we ever do it differently, it seems like a surefire waste of
  time"). A run script queues the control's tuning bench before any validation bench.
- **A bench of a new reader, judge, prompt, crop or offer is read by its rescues first**
  (AI usage, "Judged by its rescues"), then by cause, then its net.
- **Sort a probe's catches by where they sit before building on its total**: read the
  examples, then check which of them the planned integration can carry.
- **When a probe moves where the gain is, change the plan before the long run**: ask
  whether today's findings still point at the run queued yesterday.
- **Compare a retrained arbiter with production too, not only with its control**: a
  control trained beside it shares whatever the retraining changed. Before believing a
  heading miss, diff the two builds' heading lists.
- **Shared resources are shared deliberately.** PyMuPDF isn't thread-safe: hold
  `pdf.PDF_LOCK` wherever threads may meet; render on one thread, pool only model calls.
- **A cache version bumped on a branch is one no branch has used.** Before bumping,
  `git grep` the constant across all branches (`git grep -h "^FITS =" $(git branch
  --format='%(refname:short)')`); before a long run, check one output for the new field.
- **A change in how a cached value is found bumps its cache's version, and so does its
  revert.** Otherwise the cache keeps serving the other method's answer: Vanille's
  ellipsis style, measured by a method reverted on 2026-10-24, was served for 26 days.
- **Caches survive interruption.** Write them whole (`files.write_atomic`), skip a
  cut-off last line in append-only logs, version their format.

## Purpose and scope

An end-to-end tool that turns books that aren't EPUBs into clean EPUB 3 files, automated
as far as possible. The goal: an edition as careful as Standard Ebooks' (weeks of
scanning, OCR, proofreading and typesetting by people), in hours, with a human only
answering the questions the machine can't.

- **Order of attack:** scanned PDF → other formats (MOBI/AZW3, DOCX, HTML, …).
  **Born-digital PDFs are out of scope** (the user, 2026-10-17: "born digital pdfs are
  easy. they were often made in calibre using an epub as source. trivial to convert
  back. that's not the point of this project"). The pipeline still reads one (its text
  layer is exact, so the OCR check skips it), but no pair of that kind is scored.
- **Content order:** prose/fiction first; footnotes, figures, tables, verse later.
- **Book languages:** Dutch and English.
- **Fidelity:** exact wording and spelling, original paragraphs, italics and scene breaks,
  and the print's own typography: its dash and spacing, its ellipsis, its quote marks. No
  house style (Standard Ebooks restyles; this project doesn't). Drop print artefacts (page
  numbers, running heads, line-end hyphens). Fix only clear OCR errors; never "improve"
  the author's text. A misprint (the printer's slip, "zeI" for "zei") is corrected only
  where the reviewer marks it, in the book's errata (`errata.py`), never by the machine.
- **Non-goals (for now):** loose photo folders, dewarping phone photos, cloud models,
  non-Latin scripts.

### Current target book

*Wij doden Stella* by Marlen Haushofer (Dutch). We iterate until this one comes out
right, then expand.

- Internet Archive scan (Scribe), 76 pages, 325×554 pt, 360 ppi MRC layers (JPX
  background/foreground + JBIG2 mask).
- Pages: 1 cover · 2–3 scan noise and IA stamp · 4 colophon · 5–71 body (one continuous
  text, no headings or scene breaks; page 5 is a sunk opening) · 72–75 blank or library
  barcode · 76 back cover. Page sizes differ per page (crops).
- Has a **hidden OCR text layer** (GlyphLessFont) of decent quality. Observed errors: page
  number "10" → "Io", missing spaces ("vijfjaar"), missing accents ("scenes" for
  "scènes"), line-end hyphenation, indented paragraph starts, specks read as characters
  ("haar-hadden", a stray "»"), a smudge read as "><". Pages 5–9 have no page number in
  the text layer.
- That text layer is one OCR candidate among several, not the truth.

## Stack and conventions

- Python 3.13, managed with **uv**. Package and CLI are both named `roboscriptorium`.
- Layout: `src/roboscriptorium/` (src layout), tests in `tests/`, throwaway probes and
  training scripts in `experiments/`, frozen tryout sets in `tryouts/`, golden books in
  `golden/`, books and every cache under `work/` (gitignored).
- HTTP: `httpx`. Tests inject `httpx.MockTransport`, so unit tests never need a running
  model server.
- Lint/format: `ruff` (line length 100; `experiments/` excluded). Tests: `pytest`.
- Settings: `config.py`'s `Settings`, each overridable by a `ROBO_*` variable it lists
  (`ROBO_OLLAMA_URL`, `ROBO_READ_MODEL`, `ROBO_JUDGE_MODEL`, `ROBO_SORTER`,
  `ROBO_OCR_TRUST`, `ROBO_OCR_QUESTIONS`, `ROBO_OCR_ASK_BELOW`, …). `ROBO_BENCH_WORKERS`
  (how many books `bench` scores at once; one fewer than the cores) is no build setting
  and lives in `bench.py`.

The map by group; [docs/modules.md](docs/modules.md) has every module in full: read a
module's entry there before changing it.

| Group | Modules |
| --- | --- |
| the CLI, settings, a book and its `book.toml`, the user's builds pausing the agent's, a slow stage's progress | `cli`, `config`, `book`, `files`, `priority`, `progress` |
| model clients | `clients/` (`ollama`, `decide`, `llama`, `openrouter`, `retry`) |
| the page: text layer, layout, type | `pdf`, `page`, `scanpages`, `layout`, `typestyle`, `faint`, `missing` |
| line roles | `roles`, `sorter`, `sorterdata`, `pageroles` |
| readers, judges, offers measured on the scan, the arbiter | `readers`, `pagereader`, `ocrcheck`, `ocrdoubts`, `trust`, `trustdata`, `contextjudge`, `rendercheck`, `accentmarks`, `quotemarks`, `speckmarks`, `lexicon` |
| the reviewer's answers and misprints | `corrections`, `errata`, `quotes` |
| structure | `footnotes`, `epigraphs`, `chapters`, `pagekinds`, `bookinit` |
| lines into a book | `reflow`, `hyphens`, `typography`, `italics`, `figures`, `initials`, `ir`, `epub`, `epubdiff`, `pipeline` |
| review | `flags`, `review`, `structure` |
| measuring | `golden/`, `evaluate`, `disagreements`, `quality`, `bench`, `errorlog` |

## Architecture

`pipeline.run` builds a book stage by stage, each cached under `work/<book>/stages/` so
a rerun skips finished work and model calls. Before changing a stage, its order or its
model, read [docs/how-it-works.md](docs/how-it-works.md) (each stage in prose) and
`docs/pipeline.d2` (the drawing, with the model behind each stage). Not built yet:
image preprocessing (deskew, spreads), formats other than PDF.

## AI usage

**How a new decision gets added:** prototype the question, collect a labelled set (from a
golden book, or by labelling with a large generative model on Ollama when there is none),
refine the rubric (option wording plus features the model can't see, such as repetition
across pages), then measure the decision model against that set. **Start with ~10–60
items and scale up only once the results justify it.** Enforce in code what is true by
definition (a chapter heading appears once) rather than hoping the model weighs it.

**Model roles.** Every model has a role, and the docs, the diagram and talk with the
user refer to it by that role (docs/how-it-works.md):

| Role | Model | Job |
| --- | --- | --- |
| spotter | DocLayout-YOLO | marks figures, captions, titles and furniture on the page image |
| reader | glm-ocr, tesseract, qwen3.8 | reads text from the scan (also a line the layer missed) |
| sorter | clef-flash:9b | decides each doubtful line's role; guesses a drawn initial |
| judge | clef:27b, autotrust-jev 35B, d3 9B, render and compare (no model: `rendercheck.py`), Winnow-12B, autotrust-jev 9B (the text question), the word list | picks a version of a suspect; clef 27B also settles the lines two sets of line-role trees call differently |
| arbiter | the trust model (`trust.py`) | fixes, keeps or asks, weighing readers and judges |
| reviewer | the user | answers what the arbiter is unsure of |

**Every new model gets two questions.** Can it replace a model in a role we have? And
could the application improve by *adding* it: as another reader or judge beside the ones
in use, which the arbiter weighs, or as the model for a decision still made by hand, by
`book.toml` or by a rule? List both kinds of use, rank them by what they could gain, and
screen the best on the frozen sets (`experiments/tryout.py run reader|judge`). A new
reader or judge reaches the arbiter only after the trust data is rebuilt and the arbiter
retrained. Record the verdict in [docs/models.md](docs/models.md): the model for each
role is chosen by its score on golden pages, then pinned (never `latest`).

### Judged by its rescues

A **rescue** is a silent error that a source of versions brings to a fix or a question
where nothing in use does. Every source is judged by its rescues, whatever its own error
rate: a model, a reader, a prompt, a crop, a judge, an offer measured on the scan (the
user, 2026-11-08: "it doesn't matter how poorly they score individually. there is
strength in numbers"; 2026-11-15: "'worse' individually doesn't make them worse for the
whole. do they bring a fresh perspective?"). The judges and the arbiter turn a weak
source's disagreements into right answers; a source that only repeats the others adds
nothing however accurate.

A verdict on a source, in a report, decisions.md or models.md, gives in this order:

1. **Its rescues**, counted and with examples: for a reader, prompt, crop or offer,
   `experiments/silent_screen.py` (minutes: the silent errors it reads as the print
   does, the clean lines it reads otherwise; rebuild its set with `build` when the
   bench's baseline moves); for a judge, the panel's shared misses it gets right and the
   lift it gives beside the other weak candidates, with an interval from resampling
   books (`experiments/judge_overlap.py`, `judge_sheet.py`, `judge_panel_bootstrap.py`).
2. **A bench of it by cause**, fixed and made (`bench-diff`), before its net and its
   verdict line. A cost in a cause the source doesn't touch belongs to another component
   (the retrained arbiter's punctuation swaps beside accent offers, 2026-11-16): name
   that component as what failed.
3. **What is settled and what is open.** "Not taken" names the configuration that was
   benched (this arbiter, these offers together). The source is dropped only when it
   has no rescues in any combination; until then the entry says which run would settle
   it, and that run is queued.

A verdict is done when all three are in it. autotrust-jev 9B, level with Winnow alone,
was the one candidate to lift the judge panel (+0.011, interval clear of zero); d1 3B
and d1-omni 2B, tested the same way, added nothing.

Two kinds of model, used for different jobs:

- **Decision models ("System One")**, on Ollama's `/v1/systemone`. Answer bounded
  questions whose options are declared in advance, with a typed answer and a
  probability. They generate no text.
- **Generative models ("System Two")**, on Ollama. Produce text: vision-LLM OCR,
  OCR-error correction, structure and metadata.

**Rule: if the answer comes from a list that's known in advance, ask a decision model.
If it needs new text, a generative one.** Never prompt an LLM and parse its prose for a
decision a decision model can make.

### Decision models

clef and clef-flash answer on Ollama's `/v1/systemone`; every question the pipeline asks
is a `choice`. Winnow-12B, a plain GGUF without the `decision` capability, is asked the
same questions through its answer's token probabilities (`tokens:<model>`,
`clients/decide.py`; docs/models.md, Setup).

- Images: raw base64 PNG, JPEG or WebP in `images`, one per request.
- Question types: `choice` (probability per declared option), `score` (ordinal scale),
  `noul` (probability that a statement is true).

```sh
curl http://127.0.0.1:11434/v1/systemone -d '{
  "model": "clef-flash:9b",
  "state": "<text, or JSON describing the situation>",
  "questions": {"role": {"type": "choice", "instructions": "...",
                "criteria": {"page_number": "...", "body": "..."}}}
}'
```

The response holds `answers.<name>.choice`, `confidence` and `probabilities`.

- **Give decisions context.** A bare string is ambiguous. Pass a JSON state with the
  candidate plus its position on the page, its neighbouring lines and the page type.
  Confidence is **not** correctness: calibrate thresholds on golden pages before
  trusting them.
- `noul` answers carry only `noul` (P(true)). `choice` and `score` carry `confidence`
  and `probabilities`. `DecisionClient.decide` normalises all three into
  `Answer(type, value, confidence, probabilities)`.

## Environment

- Apple M4 Max, 64 GB RAM, macOS. Ollama drains the battery even on the charger, and Low
  Power Mode slows runs by half or more (docs/run-times.md): say before chaining long runs
  during the day. Every model run waits while the battery is under 30%, checking hourly
  (`experiments/battery_gate.sh`, which `timed.sh` calls first; run it before any model
  job started another way). While runs go, `experiments/battery_guard.sh` (screen
  `robo-battery-guard`, with a watcher) stops them under 30% and continues them at 50%:
  on a charger under 140 W the battery still drains under Ollama. It also stops them while
  the disk has under 5 GB free, until 15 GB: a model download can fill it mid-run.
- **An unanswered question never holds the machine** (the user, 2026-11-14, after a night
  idle while "may I start the overnight runs?" went unanswered: "unforgivable"). Silence
  is not a no: the user is asleep or away, and the battery gate guards the charge. Runs
  already on the checklist start without waiting for a yes; a question asked at night is
  answered by starting the runs and saying so. A review server left open whose answers are
  all saved (the verdict file unchanged since) is no open review: bench beside it, and say
  not to press "Rebuild book" until the run ends.
- Ollama (Homebrew's `ollama-app` cask, and the `ollama` formula for the CLI) at
  `http://127.0.0.1:11434`, not pinned: it updates itself (the user, 2026-11-08). After an
  update, `roboscriptorium doctor` checks that the decision models still answer before a
  long run relies on them (0.40.4 refused GGUF-made decision models, docs/models.md, Setup).
  **Agents may quit, kill and restart Ollama at will** (the user, 2026-11-08: "now and
  forever"), with `experiments/ollama-restart.sh`: a runner stuck in "Stopping..." holds up
  every other model's requests without ever timing out (2026-11-08, two hours). A run in
  flight resumes from its caches. Watchers on model runs report a stall (no answer cached
  for 20 minutes), and a stall with a runner stuck stopping is restarted, not waited on.
  Never with sudo (the user: it needs them at the keyboard): Ollama runs as the user, and
  the script needs no elevated rights.
  Context length 32k in the
  app's settings; `OLLAMA_NUM_PARALLEL=4` (`launchctl setenv`, read when the app starts).
- Present: `uv`, `python3`, `pandoc`, calibre `ebook-convert`, poppler (`pdfinfo`,
  `pdftotext`, `pdfimages`), epubcheck, d2, llama.cpp's `llama-server` (all Homebrew where
  applicable); scikit-learn and the dependency group `layout` (`doclayout-yolo` with
  PyTorch) in Python.
- Model weights live outside `~/code` (backed up hourly): models we train or download by
  hand in `~/models/roboscriptorium/`, one subfolder each.
- Models set up by hand or kept in an environment of their own (Winnow-12B, `imajev:4b`,
  imajev on `llama-server`, Kraken, LightOnOCR-3, the
  DocLayout-YOLO weights): [docs/models.md](docs/models.md), Setup.
- Fonts: `work/fonts/`, the user's library of book typefaces (2,419 OpenType and TrueType
  files, 407 MB: Adobe Font Folio 11 and `extra/` with Quadraat, Scala and Swift), for
  drawing a reading as the book prints it (`rendercheck.py`, `ROBO_FONTS`). Licensed:
  never in git, like the books.
- Word lists: `work/lexicon/{nld,eng}-words.txt`, built by `lexicon.py` from the tessdata
  models with `combine_tessdata` and `dawg2wordlist` (both come with Homebrew's
  tesseract).
- tesseract 5.5.3 (Homebrew, `eng`/`osd` only). The Dutch model is `nld.traineddata`
  from tessdata_best in `work/tessdata/` (pass `--tessdata-dir work/tessdata`);
  `tesseract-lang` (~650 MB) is not installed.

## Running, reviewing, evaluating

A book lives in `work/<book>/` with `source.pdf` and a `book.toml`:

```toml
title = "Wij doden Stella"
author = "Marlen Haushofer"
language = "nl"
translator = "Ria van Hengel"   # optional: as the colophon names them
cover_page = 1
body_pages = [5, 71]   # inclusive; page classification replaces this later
dash = "–"             # optional: how the book prints dashes ("–" or "—") …
dash_spacing = "thin"  # … and their gaps ("none", "thin", "word"); else measured
ellipsis = "..."       # optional: "…", "..." or ". . ." …
ellipsis_space = false # … and a space before it; else measured on the scan
blank = "..."          # optional: what a printed blank ("het __plein") becomes
typeface = "Adobe Font Folio 11/Western Fonts/Sabon/SabonLTStd-Roman.otf"  # optional: a
                       # file in work/fonts, drafted by `init`; else matched on the scan
```

```sh
uv run roboscriptorium doctor            # is Ollama up, and do its decision models answer?
uv run roboscriptorium build work/stella # → work/stella/stella.epub, kept dated in work/stella/epubs/
epubcheck work/stella/stella.epub        # must report 0 errors / 0 warnings
uv run ruff format . && uv run ruff check . && uv run pytest
```

**Reviewing a book.** `uv run roboscriptorium review work/<book>` builds the book and
serves its questions on http://127.0.0.1:8765/, next to scan crops; the page and its keys
are in [docs/how-it-works.md](docs/how-it-works.md) (Review). "Rebuild book" applies the
answers. A misprint (`m`) goes to `work/<book>/errata.toml`, which can be edited by
hand; an entry that doesn't match once stops the build. `--find "<words>"` adds the
lines holding those words as questions (a misprint seen while reading); `--only <json>` on a
golden book asks just the places a list of bench error rows names, those settled by kind too
(`experiments/review_batch_commands.py` prints one command per book). **Sample the questions before
sending the user to review** (`experiments/sample_questions.py <book>` lays them out with
their crops): never obvious ones.

### Golden books

A golden pair is a scan and a human-checked reference text of the same printing
(Project Gutenberg's transcription or the publisher's own EPUB); every change is
measured against the pairs. Always in force:

- A public-domain pair lives whole in `golden/<name>/` in git. A book in copyright
  (`eu_copyright_until` in its manifest) keeps its text and its verdicts in
  `work/golden/<name>/`: human answers that exist nowhere else. Scans are never
  committed.
- **A new pair waits for its first look**: one score, untouched by anything before it
  (no eval, quality, review, bench, trust data or probe; `build` may warm its caches).
  `eval`, `quality`, `review` and `bench first-look` refuse it without `--first-look`.
- Tuning books are chosen on; validation books only veto; `bench quick` is a change's
  short test and never sees front matter, mottos or picture pages.
- A suspect pair (a bench names it) is said in the session's report with a proposal to
  retire it, unasked.

Before adding, fetching, deriving, slicing, retiring or reviewing a pair, checking a
candidate, handling a deviation between an e-book and its print, or reading verdicts
and disagreements, read [docs/golden-notes.md](docs/golden-notes.md), "Working with
golden pairs": the commands and the rules for each.
