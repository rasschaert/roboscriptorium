"""Do the judges make the same mistakes? On judge set v2: each judge's error rate,
weighted back to the real mix of suspects; for each pair, how often one is wrong where
the other is, and with the same wrong pick; and a quorum (the most common pick, ties to
clef). No models.

    uv run python experiments/judge_overlap.py

Then each judge's errors by what the versions differ in and by language, the places
only it gets right, and those every judge gets wrong, with examples.
"""

import itertools
import json
from collections import Counter
from pathlib import Path

ROOT = Path("work/tryout/judge-v2")
L = "abcdefg"
JUDGES = {
    "clef": None,
    "clef wide": "clef_27b+wide",
    "pplx 27B": "pplx-decider_27b-nvfp4",
    "pplx flash": "pplx-decider-flash_4b-nvfp4",
    "winnow (text)": "",
}


def main() -> None:
    data = json.loads((ROOT / "items.json").read_text())
    items, books = data["items"], data["books"]
    for name in list(JUDGES):
        f = ROOT / "answers" / f"{JUDGES[name]}.json"
        if JUDGES[name] and not f.exists():
            del JUDGES[name]
    for extra in sorted((ROOT / "answers").glob("*.json")):
        if extra.stem not in JUDGES.values() and "+" not in extra.stem:
            JUDGES[extra.stem] = extra.stem
    answers = {}
    for name, stem in JUDGES.items():
        if stem is None:
            answers[name] = {i["id"]: i["incumbent"]["value"] for i in items}
        elif stem == "":
            answers[name] = {i["id"]: i["text_incumbent"]["value"] for i in items}
        else:
            got = json.loads((ROOT / "answers" / f"{stem}.json").read_text())
            answers[name] = {k: v["value"] for k, v in got.items()}
    items = [i for i in items if all(i["id"] in a for a in answers.values())]
    share = sum(b["wrong"] for b in books.values()) / sum(b["settled"] for b in books.values())
    n_hard = sum(i["stratum"] == "hard" for i in items)
    # Each item's weight in the real mix of suspects.
    w = {i["id"]: share / n_hard if i["stratum"] == "hard" else (1 - share) / (len(items) - n_hard) for i in items}

    def right(i, v):
        return v in L and i["right"][L.index(v)]

    wrong = {n: {i["id"] for i in items if not right(i, a[i["id"]])} for n, a in answers.items()}
    print(f"{len(items)} suspects, weighted to the real mix (clef wrong on {share:.1%})")
    for n in answers:
        print(f"  {n:16} wrong {sum(w[k] for k in wrong[n]):.1%}")
    print("P(B wrong | A wrong), and P(same wrong pick | both wrong):")
    for a, b in itertools.permutations(answers, 2):
        both = wrong[a] & wrong[b]
        same = sum(answers[a][k] == answers[b][k] for k in both)
        pa = sum(w[k] for k in wrong[a])
        print(f"  {a:16} → {b:16} {sum(w[k] for k in both) / pa:5.0%}   same pick {same / max(len(both), 1):4.0%}")
    for panel in [list(answers)] + [list(c) for c in itertools.combinations(answers, 3)]:
        acc = 0.0
        for i in items:
            votes = Counter(answers[n][i["id"]] for n in panel)
            top = max(votes.values())
            picks = [v for v, c in votes.items() if c == top]
            pick = answers["clef"][i["id"]] if answers["clef"][i["id"]] in picks else picks[0]
            acc += w[i["id"]] * right(i, pick)
        print(f"  quorum of {', '.join(panel):60} right {acc:.1%}")




def by_kind() -> None:
    """Each judge's errors by what the versions differ in, and the places only it gets
    right, with examples."""
    import random
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from tryout import difference_kind

    data = json.loads((ROOT / "items.json").read_text())
    items, books = data["items"], data["books"]
    answers = {}
    for name, stem in JUDGES.items():
        if stem is None:
            answers[name] = {i["id"]: i["incumbent"]["value"] for i in items}
        elif stem == "":
            answers[name] = {i["id"]: i["text_incumbent"]["value"] for i in items}
        elif (ROOT / "answers" / f"{stem}.json").exists():
            got = json.loads((ROOT / "answers" / f"{stem}.json").read_text())
            answers[name] = {k: v["value"] for k, v in got.items()}
    items = [i for i in items if all(i["id"] in a for a in answers.values())]
    share = sum(b["wrong"] for b in books.values()) / sum(b["settled"] for b in books.values())
    n_hard = sum(i["stratum"] == "hard" for i in items)
    w = {i["id"]: share / n_hard if i["stratum"] == "hard" else (1 - share) / (len(items) - n_hard) for i in items}

    def right(i, v):
        return v in L and i["right"][L.index(v)]

    kinds = {i["id"]: difference_kind(i["state"]["readings"]) for i in items}
    lang = {i["id"]: "nl" if i["book"] not in ENGLISH else "en" for i in items}
    names = list(answers)
    print("\nwrong, weighted to the real mix, by what the versions differ in (share of suspects):")
    groups = sorted(set(kinds.values())) + ["nl", "en"]
    print(f"  {'':14}" + "".join(f"{g:>13}" for g in groups))
    tot = {g: sum(w[i["id"]] for i in items if g in (kinds[i["id"]], lang[i["id"]])) for g in groups}
    print(f"  {'(share)':14}" + "".join(f"{tot[g]:>13.0%}" for g in groups))
    for n in names:
        row = []
        for g in groups:
            sel = [i for i in items if g in (kinds[i["id"]], lang[i["id"]])]
            bad = sum(w[i["id"]] for i in sel if not right(i, answers[n][i["id"]]))
            row.append(f"{bad / tot[g]:>13.1%}")
        print(f"  {n:14}" + "".join(row))
    print("\nright where every other judge is wrong (count, by kind), with examples:")
    rng = random.Random(0)
    for n in names:
        only = [i for i in items if right(i, answers[n][i["id"]])
                and not any(right(i, answers[m][i["id"]]) for m in names if m != n)]
        c = Counter(kinds[i["id"]] for i in only)
        print(f"  {n:14} {len(only):3}  {dict(c)}")
        for i in rng.sample(only, min(4, len(only))):
            v = i["state"]["readings"]
            print(f"      {i['book'][:22]:22} p{i['state']['page']:<4} {v}  right: {v[i['right'].index(True)]!r}")
    print("\nwrong where every judge is wrong (count, by kind), with examples:")
    allwrong = [i for i in items if not any(right(i, answers[m][i["id"]]) for m in names)]
    print(f"  {len(allwrong)}  {dict(Counter(kinds[i['id']] for i in allwrong))}")
    for i in rng.sample(allwrong, min(10, len(allwrong))):
        v = i["state"]["readings"]
        r = [x for x, ok in zip(v, i["right"]) if ok]
        print(f"      {i['book'][:22]:22} p{i['state']['page']:<4} {v}  right: {r}")


ENGLISH = {
    "the-story-of-doctor-dolittle--stokes-1920",
    "the-thief-takers-apprentice--ia-scan",
    "metro-2033--ia-scan",
    "artemis--ia-scan",
}

if __name__ == "__main__":
    main()
    by_kind()
