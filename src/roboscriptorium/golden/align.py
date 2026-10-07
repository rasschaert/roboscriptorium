"""Labels for a golden scan's lines: the reference words each text-layer line holds.

The text layer's words, line by line in page order, are aligned with the
reference's words (headings and paragraphs, in order). A line gets the reference
words aligned to its own words: its true text, typos of the layer corrected. Its
role follows: a heading when its words align with a chapter heading, other (page
furniture, stamps, noise) when most of its words align with nothing, else body.
Labels come from the text layer as read, so they key on its line positions.
"""

from dataclasses import dataclass

from rapidfuzz.distance import Levenshtein

from roboscriptorium.evaluate import normalise
from roboscriptorium.golden.reference import Chapter, unmarked
from roboscriptorium.ir import SourceRef
from roboscriptorium.pdf import PageText

# A line is furniture when fewer than this share of its words align with reference words.
BODY_SHARE = 0.5
# A layer word misread from a reference word still shares this much of it.
SIMILAR = 0.5


@dataclass(frozen=True)
class LineTruth:
    truth: str  # the reference words aligned to the line ("" for none)
    role: str  # "body", "heading" or "other"


def align(pages: list[PageText], reference: list[Chapter]) -> dict[SourceRef, LineTruth]:
    out_words: list[str] = []
    out_lines: list[SourceRef] = []
    for p in pages:
        for k, line in enumerate(p.lines):
            for w in normalise(line.text).split():
                out_words.append(w)
                out_lines.append(SourceRef(p.number, k))
    ref_words: list[str] = []  # normalised, for matching
    ref_print: list[str] = []  # as the reference has them, for the truth
    in_heading: list[bool] = []
    for ch in reference:
        for text, heading in [(ch.heading, True)] + [(unmarked(p), False) for p in ch.paragraphs]:
            words, printed = normalise(text).split(), text.split()
            ref_words += words
            ref_print += printed if len(printed) == len(words) else words
            in_heading += [heading] * len(words)

    # Per line: the reference words (or parts of one) it holds, with their indices,
    # and how many of its own words matched.
    held: dict[SourceRef, list[tuple[int, str]]] = {ref: [] for ref in dict.fromkeys(out_lines)}
    matched: dict[SourceRef, int] = dict.fromkeys(held, 0)
    for (o0, o1), (r0, r1) in _blocks(out_words, ref_words):
        if r0 == r1:
            continue
        if o0 == o1:
            # Words only the reference has go with the line before them.
            if out_lines:
                held[out_lines[max(0, o0 - 1)]] += [(j, ref_print[j]) for j in range(r0, r1)]
            continue
        # Each reference word goes to the most similar layer word not before the
        # previous one's; a layer word that resembles its reference word matched.
        # A word the layer breaks over a line end is broken the same way.
        i = o0
        for j in range(r0, r1):
            i = max(
                range(i, o1),
                key=lambda k: max(
                    _similarity(out_words[k], ref_words[j]),
                    _joined(out_words, out_lines, k, o1, ref_words[j])[1],
                ),
            )
            split = _line_break(out_words, out_lines, i, o1, ref_words[j], ref_print[j])
            if split:
                for k, part in ((i, split[0]), (i + 1, split[1])):
                    held[out_lines[k]].append((j, part))
                    matched[out_lines[k]] += 1
                i += 1
                continue
            held[out_lines[i]].append((j, ref_print[j]))
            if _similarity(out_words[i], ref_words[j]) >= SIMILAR:
                matched[out_lines[i]] += 1

    total = dict.fromkeys(held, 0)
    for ref in out_lines:
        total[ref] += 1
    labels = {}
    for ref, indices in held.items():
        if matched[ref] < BODY_SHARE * total[ref]:
            role = "other"
        elif indices and sum(in_heading[j] for j, _ in indices) * 2 > len(indices):
            role = "heading"
        else:
            role = "body"
        truth = " ".join(part for _, part in indices) if role != "other" else ""
        labels[ref] = LineTruth(truth, role)
    return labels


HYPHENS = "-\u00ad\u00ac"


def _line_break(
    out: list[str], lines: list[SourceRef], i: int, end: int, word: str, printed: str
) -> tuple[str, str] | None:
    """The printed word's two parts when the layer breaks it after `out[i]`, the last
    word of its line: "ge-" + "luid" for "geluid", "wc-" + "rol" for "wc-rol"."""
    joined, score = _joined(out, lines, i, end, word)
    if score <= _similarity(out[i], word):
        return None
    head = out[i][:-1]
    cut = round(len(printed) * len(head) / max(1, len(joined)))
    if printed.lower().startswith(head.lower()):
        cut = len(head)
    if cut < len(printed) and printed[cut] == "-":
        return printed[: cut + 1], printed[cut + 1 :]
    return printed[:cut] + "-", printed[cut:]


def _joined(out: list[str], lines: list[SourceRef], i: int, end: int, word: str):
    """`out[i]` joined with the next line's first word, if it ends its line in a hyphen,
    with or without the hyphen, whichever is nearer `word`; and its similarity."""
    if i + 1 >= end or lines[i + 1] == lines[i] or not out[i] or out[i][-1] not in HYPHENS:
        return "", 0.0
    joined = max(out[i][:-1] + out[i + 1], out[i] + out[i + 1], key=lambda w: _similarity(w, word))
    return joined, _similarity(joined, word)


def _similarity(a: str, b: str) -> float:
    return Levenshtein.normalized_similarity(a, b)


def _blocks(out: list[str], ref: list[str]):
    """Aligned stretches ((out start, end), (ref start, end)): equal ones word by word,
    and each run of differing operations as one block, so that similarity, not
    position, pairs a misread word with its reference word."""
    run = None
    for op in Levenshtein.opcodes(out, ref):
        if op.tag == "equal":
            if run:
                yield run
                run = None
            for k in range(op.src_end - op.src_start):
                i, j = op.src_start + k, op.dest_start + k
                yield (i, i + 1), (j, j + 1)
        elif run is None:
            run = ((op.src_start, op.src_end), (op.dest_start, op.dest_end))
        else:
            run = ((run[0][0], op.src_end), (run[1][0], op.dest_end))
    if run:
        yield run
