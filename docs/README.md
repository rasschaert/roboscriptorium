# The docs

Start with the **[primer](primer.md)**. It explains the whole project from first
principles, with pictures, in about half an hour. Most of the other files are for
looking things up, not for reading from start to end.

## To understand the machine

| File | What it tells you | Read it |
| --- | --- | --- |
| **[primer.md](primer.md)** | the problem, the ideas, how a change is judged, where the gains are expected, the vocabulary | first, all of it |
| [how-it-works.md](how-it-works.md) | one book followed through every stage, with the [diagram](pipeline.svg) of the stages and the model behind each | second, when you want the detail |
| [design.md](design.md) | why each part is there, and the measurements that earn it its place | per part, when you wonder "why this?" |
| [models.md](models.md) | every model tried, by role, with its verdict | when a model comes up |
| [modules.md](modules.md) | the code, module by module | before changing code |

## Where things stand

| File | What it tells you |
| --- | --- |
| [outlook.md](outlook.md) | how close the build is, where results can still move, what was tried without effect |
| [optimism.md](optimism.md) | how likely the goal looks, answered each time it's asked, dated |
| [checklist.md](checklist.md) | the plan: every open step in order, who does it, how long; what's done below it |

## The golden books

The scans with a checked text that every change is measured on (the primer explains
them).

| File | What it tells you |
| --- | --- |
| [golden-books.md](golden-books.md) | their numbers, one table, generated |
| [golden-notes.md](golden-notes.md) | each book's edition and quirks, and how to work with them |

## The record

Long, dated, and only ever looked up: search them, don't read them.

| File | What it tells you |
| --- | --- |
| [decisions.md](decisions.md) | everything learned or decided, with its numbers, oldest first |
| [run-times.md](run-times.md) | how long each long run took, to estimate the next |
| [hosted-inference.md](hosted-inference.md) | the plan if free hosted model time ever comes |

The [primer/](primer/) folder holds the primer's figures; `pipeline.d2` is the source of
the stage diagram. Agents working on the code start from `AGENTS.md` and `HANDOVER.md`
at the top of the repository.
