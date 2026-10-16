"""The OCR check's suspects as review questions: one place in a line (`doubts`) or a
whole line with every source's version of it (`line_doubts`)."""

from collections import Counter
from dataclasses import dataclass

from roboscriptorium.ocrcheck import Suspect, across


@dataclass(frozen=True)
class Doubt:
    """One place in a line where the readings differ and no model settled it: one question."""

    page: int
    line: int  # index into the page's lines, after missing lines were added
    original: str  # the line as the text layer reads it (glm-ocr's for an added line)
    start: int  # the place, as a span of `original`
    end: int
    box: tuple[float, float, float, float]
    # The whole line as each reading has it here (the text layer's first), with the
    # models that picked it; the rest of the line as the text layer reads it.
    readings: list[tuple[str, list[str]]]
    # For a break hyphen: the next line's first word, which the readings end with.
    joined: str = ""
    # The line's other places the OCR check changed or asks about, as spans of
    # `original`: (start, end, text, "fixed" or "asked"), the text an asked place's
    # likeliest version. Shown beside the readings only; an answer keeps to its place.
    elsewhere: tuple[tuple[int, int, str, str], ...] = ()


def _likeliest(s: Suspect) -> str:
    """The version of a suspect most models picked, the text layer's on a tie."""
    versions = [s.ours, *s.others]
    picks = Counter(v for v in s.votes.values() if v in versions)
    return max(versions, key=lambda v: (picks[v], v == s.ours))


def _elsewhere(s: Suspect, suspects: list[Suspect]) -> tuple[tuple[int, int, str, str], ...]:
    """The other places in `s`'s line that a reader of its question should see settled."""
    out = []
    for o in suspects:
        if (o.page, o.line, o.original) != (s.page, s.line, s.original) or o is s:
            continue
        if o.end <= s.start or o.start >= s.end:
            if o.choice == "review":
                out.append((o.start, o.end, _likeliest(o), "asked"))
            elif o.choice == "other" and o.chosen is not None:
                out.append((o.start, o.end, o.chosen, "fixed"))
    out.sort()
    # Places that overlap each other can't both be shown in one line.
    return tuple(p for k, p in enumerate(out) if k == 0 or p[0] >= out[k - 1][1])


def doubts(suspects: list[Suspect]) -> list[Doubt]:
    """A question per place a human should settle."""
    out = []
    for s in suspects:
        if s.choice != "review":
            continue
        readings: list[tuple[str, list[str]]] = []
        for version in (s.ours, *s.others):
            line = s.original[: s.start] + across(version, s.joined) + s.original[s.end :]
            voters = [model for model, picked in s.votes.items() if picked == version]
            known = next((r for r in readings if r[0] == line), None)
            if known is None:
                readings.append((line, voters))
            else:
                known[1].extend(v for v in voters if v not in known[1])
        out.append(
            Doubt(
                s.page,
                s.line,
                s.original,
                s.start,
                s.end,
                s.box,
                readings,
                s.joined,
                _elsewhere(s, suspects),
            )
        )
    return out


# The second readings' names in `Suspect.support`, as the review shows them.
READER_NAMES = {"glm": "glm-ocr", "qwen": "Qwen", "tess": "tesseract"}


def line_doubts(suspects: list[Suspect]) -> list[Doubt]:
    """A question per line a human should settle, however many places in it are in
    doubt: the whole line as the text layer reads it, as each reader and each judge has
    it at every doubtful place, with each place as most models read it, and as the build
    has it, alike ones merged. A line
    ending in a break hyphen keeps its own last word, not the one read across the break.
    """
    by_line: dict[tuple[int, int], list[Suspect]] = {}
    for s in suspects:
        by_line.setdefault((s.page, s.line), []).append(s)
    out = []
    for (page, line), here in sorted(by_line.items()):
        if not any(s.choice == "review" for s in here):
            continue
        readers = dict.fromkeys(n for s in here for n in s.support)
        judges = dict.fromkeys(m for s in here for m in s.votes)
        # Where a source has no say, its line is as built.
        built = [s.chosen if s.choice == "other" else s.ours for s in here]
        sources = [("text layer", [s.ours for s in here])]
        sources += [
            (READER_NAMES.get(n, n), [_read_by(s, n, b) for s, b in zip(here, built, strict=True)])
            for n in readers
        ]
        sources += [
            (m, [s.votes.get(m) or b for s, b in zip(here, built, strict=True)]) for m in judges
        ]
        # Each doubtful place as most models read it: the line no single reader may have.
        sources.append(
            (
                "likeliest",
                [
                    _likeliest(s) if s.choice == "review" else b
                    for s, b in zip(here, built, strict=True)
                ],
            )
        )
        sources.append(("as built", built))
        readings: list[tuple[str, list[str]]] = []
        for label, versions in sources:
            text = _with_versions(here, versions)
            known = next((r for r in readings if r[0] == text), None)
            if known is None:
                readings.append((text, [label]))
            elif label not in known[1]:
                known[1].append(label)
        if len(readings) < 2:
            continue
        boxes = [s.box for s in here]
        box = (
            min(b[0] for b in boxes),
            min(b[1] for b in boxes),
            max(b[2] for b in boxes),
            max(b[3] for b in boxes),
        )
        out.append(Doubt(page, line, here[0].original, 0, len(here[0].original), box, readings))
    return out


def _read_by(s: Suspect, reader: str, otherwise: str) -> str:
    """The version of a suspect `reader` reads, `otherwise` where it reads none."""
    reads = s.support.get(reader, ())
    return next((v for v, r in zip([s.ours, *s.others], reads, strict=False) if r), otherwise)


def _with_versions(here: list[Suspect], versions: list[str]) -> str:
    """The line with each suspect's span set to its version (one suspect each)."""
    text = here[0].original
    for s, v in sorted(zip(here, versions, strict=True), key=lambda sv: -sv[0].start):
        text = text[: s.start] + v + text[s.end :]
    return text
