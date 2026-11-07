"""Every judge's pick on every suspect of judge set v2 where any judge is wrong: the crop,
the versions, the right one, each judge's pick and confidence. Grouped by who gets it
wrong (all, only one, …), so the exact mistakes each model makes sit side by side. Also
written as a TSV for scripts. No models; rerun after a screen adds answers.

    uv run python experiments/judge_sheet.py
    open work/probes/judge-v2/sheet.html
"""

import base64
import csv
import json
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tryout import difference_kind, sha  # noqa: E402

ROOT = Path("work/tryout/judge-v2")
OUT = Path("work/probes/judge-v2")
L = "abcdefg"


def judges(items: list[dict]) -> dict[str, dict[str, dict]]:
    """Each judge's answers by suspect id: clef and Winnow from the set, the rest from the
    screens (plain answers of any model, and clef's and pplx's wide crop)."""
    out = {
        "clef": {i["id"]: i["incumbent"] for i in items},
        "winnow (text)": {i["id"]: i["text_incumbent"] for i in items},
    }
    for f in sorted((ROOT / "answers").glob("*.json")):
        stem = f.stem
        if "+" in stem and not stem.endswith("+wide"):
            continue
        if stem.startswith("tokens_"):
            continue
        got = json.loads(f.read_text())
        # A screen still running would shrink the sheet to its answers so far.
        if len(got) == len(items):
            out[stem.replace("_", ":", 1).replace("+wide", " wide")] = got
    return out


def main() -> None:
    data = json.loads((ROOT / "items.json").read_text())
    items = data["items"]
    answers = judges(items)
    items = [i for i in items if all(i["id"] in a for a in answers.values())]
    names = list(answers)

    def right(i, v):
        return v in L and i["right"][L.index(v)]

    rows = []
    for i in items:
        wrong = [n for n in names if not right(i, answers[n][i["id"]]["value"])]
        if wrong:
            rows.append((i, wrong))
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "sheet.tsv").open("w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["id", "book", "page", "kind", "versions", "right", *names])
        for i, _ in rows:
            v = i["state"]["readings"]
            picks = []
            for n in names:
                a = answers[n][i["id"]]
                p = v[L.index(a["value"])] if a["value"] in L[: len(v)] else a["value"]
                picks.append(f"{p} ({a['confidence']:.2f})")
            r = [x for x, ok in zip(v, i["right"], strict=True) if ok]
            w.writerow([i["id"], i["book"], i["state"]["page"], difference_kind(v), " | ".join(v), " | ".join(r), *picks])

    def group(wrong):
        if len(wrong) == len(names):
            return "every judge wrong"
        if len(wrong) == 1:
            return f"only {wrong[0]} wrong"
        if len(wrong) == len(names) - 1:
            return f"only {next(n for n in names if n not in wrong)} right"
        return f"{len(wrong)} of {len(names)} wrong"

    groups: dict[str, list] = {}
    for i, wrong in rows:
        groups.setdefault(group(wrong), []).append(i)
    order = sorted(groups, key=lambda g: (g != "every judge wrong", not g.startswith("only"), g))
    html = [
        "<!doctype html><meta charset=utf-8><title>Judge mistakes</title><style>"
        "body{font:13px system-ui;margin:16px}table{border-collapse:collapse;margin-bottom:24px}"
        "td,th{border:1px solid #ccc;padding:3px 6px;vertical-align:middle}"
        ".ok{background:#e3f4e3}.bad{background:#f8dcdc}img{max-height:40px}"
        "th{background:#f3f3f3;position:sticky;top:0}</style>",
        f"<h1>Judge mistakes on judge set v2</h1><p>{len(rows)} of {len(items)} suspects where at "
        "least one judge picks wrong. Green: right; red: wrong; the number is the judge's "
        "confidence. Groups: "
        + ", ".join(f"<a href='#{k}'>{escape(g)} ({len(groups[g])})</a>" for k, g in enumerate(order))
        + "</p>",
    ]
    for k, g in enumerate(order):
        html.append(f"<h2 id='{k}'>{escape(g)} ({len(groups[g])})</h2><table><tr><th>crop</th>"
                    "<th>book · PDF page · kind</th><th>versions</th><th>right</th>"
                    + "".join(f"<th>{escape(n)}</th>" for n in names) + "</tr>")
        for i in sorted(groups[g], key=lambda i: (difference_kind(i["state"]["readings"]), i["book"])):
            v = i["state"]["readings"]
            png = (ROOT / "crops" / f"{sha(i['id'])}.png").read_bytes()
            r = [x for x, ok in zip(v, i["right"], strict=True) if ok]
            cells = []
            for n in names:
                a = answers[n][i["id"]]
                p = v[L.index(a["value"])] if a["value"] in L[: len(v)] else a["value"]
                cls = "ok" if right(i, a["value"]) else "bad"
                cells.append(f"<td class={cls}>{escape(p)} <small>{a['confidence']:.2f}</small></td>")
            html.append(
                f"<tr><td><img src='data:image/png;base64,{base64.b64encode(png).decode()}'></td>"
                f"<td>{escape(i['book'][:24])} · {i['state']['page']} · {difference_kind(v)}</td>"
                f"<td>{' | '.join(escape(x) for x in v)}</td><td>{escape(' | '.join(r))}</td>"
                + "".join(cells) + "</tr>"
            )
        html.append("</table>")
    (OUT / "sheet.html").write_text("\n".join(html))
    print(f"{len(rows)} suspects with a wrong pick, {len(names)} judges: {OUT}/sheet.html, sheet.tsv")
    for g in order:
        print(f"  {g:40} {len(groups[g])}")


if __name__ == "__main__":
    main()
