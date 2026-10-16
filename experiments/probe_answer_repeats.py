"""How many of a book's open questions repeat a correction the reviewer already made.

Reads the review's state (saved from a running review: `curl -s
http://127.0.0.1:8765/api/state > state.json`), takes each answered line's word changes
(original → answer, word by word), and checks every open question: whether applying
those changes to its line gives one of its readings (the question would be settled), or
touches the line without matching any reading. No models.

    uv run python experiments/probe_answer_repeats.py work/probes/answer-repeats/state.json
"""

import difflib
import json
import sys
from collections import Counter


def changes(original: str, answer: str) -> list[tuple[str, str]]:
    """The answer's word changes to the original: (words before, words after)."""
    a, b = original.split(), answer.split()
    out = []
    for tag, i0, i1, j0, j1 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag != "equal":
            out.append((" ".join(a[i0:i1]), " ".join(b[j0:j1])))
    return out


def main(path: str) -> None:
    items = json.load(open(path))["items"]
    pairs: Counter = Counter()
    for it in items:
        a = it["answer"]
        if a and a["text"] and a["text"] != it["text"]:
            pairs.update((w, r) for w, r in changes(it["text"], a["text"]) if w)
    learned = {w: r for (w, r), _ in pairs.most_common() if w}
    print(f"{len(learned)} word changes learned from {sum(1 for i in items if i['answer'])} answers")
    for (w, r), n in pairs.most_common(25):
        print(f"  {n}× {w!r} → {r!r}")
    open_ = [i for i in items if not i["answer"]]
    settled, touched = [], []
    for it in open_:
        words = it["text"].split()
        fixed = " ".join(learned.get(w, w) for w in words)
        if fixed == it["text"]:
            continue
        readings = [g["text"] for g in it["readings"]]
        (settled if fixed in readings else touched).append((it, fixed))
    print(f"\n{len(open_)} open questions: {len(settled)} settled by an earlier answer, "
          f"{len(touched)} touched without matching a reading")
    for it, fixed in settled:
        print(f"  SETTLED p{it['page']}: {it['text'][:70]!r} → {fixed[:70]!r}")
    for it, fixed in touched:
        print(f"  TOUCHED p{it['page']}: {it['text'][:70]!r} → {fixed[:70]!r}")


if __name__ == "__main__":
    main(sys.argv[1])
