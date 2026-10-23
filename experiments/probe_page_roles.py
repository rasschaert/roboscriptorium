"""Can the read model tell a page's headings from the whole page image, where the role
model, its rules and the trees miss them (chapter numbers mid-page, a narrator's name)?

On the certain rows of the tuning books (`laya_roles_data.py`): every page holding a
heading and as many without, seeded. The model sees the page and all its lines, numbered,
and names each line's kind; its answer is compared with the reference's label and the
pipeline's (`laya_roles_eval.pipeline_roles`, the trees trained without the book).

    uv run python experiments/probe_page_roles.py ask [limit] [--short]
    uv run python experiments/probe_page_roles.py score [--short]

`--short` asks only for the numbers of the heading and furniture lines (every other line is
running text): a few tokens a page instead of one label a line.

Answers are appended to work/probes/page-roles/answers-<model>.jsonl (a run resumes).
"""

import base64
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

ROOT = Path("work/probes/laya-roles")
OUT = Path("work/probes/page-roles")
KINDS = {"T": "body", "H": "heading", "F": "other", "X": "other"}
PROMPT = (
    "This is a page of a printed book. Below is every line read from it, numbered from the "
    "top. Name each line's kind from the page image and the text:\n"
    "T: the book's running text (prose, dialogue, a quotation, a paragraph's short last line)\n"
    "H: a heading of the book: a chapter, part or section title, name or number, set where "
    "it begins (often larger, spaced, centred or in capitals)\n"
    "F: page furniture: a page number or a running head\n"
    "X: anything else (a stamp, a speck, a stray mark)\n\n{lines}\n\n"
    'Answer with a JSON object from line number to kind and nothing else, for example '
    '{{"1": "F", "2": "H", "3": "T"}}.'
)


SHORT_PROMPT = (
    "This is a page of a printed book. Below is every line read from it, numbered from the "
    "top. Which lines are headings of the book (a chapter, part or section title, name or "
    "number, set where it begins, often larger, spaced, centred or in capitals), and which "
    "are page furniture (a page number, a running head) or stray marks? Every other line is "
    "running text.\n\n{lines}\n\n"
    'Answer with a JSON object and nothing else, for example {{"H": [2], "F": [1, 30]}}.'
)
SHORT = "--short" in sys.argv


def sample() -> list[tuple[str, int]]:
    from roboscriptorium import bench

    tuning = {s.split(":")[0] for s in bench.SETS["tuning"]}
    rng = random.Random(29)
    out = []
    for path in sorted(ROOT.glob("*.jsonl")):
        if path.stem not in tuning:
            continue
        rows = [json.loads(x) for x in path.read_text().splitlines()]
        with_heading = sorted({r["page"] for r in rows if r["gold"]["role"] == "heading"})
        without = sorted({r["page"] for r in rows} - set(with_heading))
        chosen = with_heading + rng.sample(without, min(len(without), len(with_heading)))
        out += [(path.stem, p) for p in sorted(chosen)]
    return out


def _answers(model: str) -> Path:
    name = model.replace(":", "_").replace("/", "_") + ("-short" if SHORT else "")
    return OUT / f"answers-{name}.jsonl"


def _kinds(found: dict, count: int) -> dict[str, str]:
    """A short answer ({"H": [...], "F": [...]}) as one kind a line."""
    out = {str(i): "T" for i in range(1, count + 1)}
    for kind in ("F", "H"):
        for i in found.get(kind, []) if isinstance(found.get(kind), list) else []:
            out[str(i)] = kind
    return out


def ask(limit: int | None) -> None:
    import httpx
    import pymupdf

    from roboscriptorium import pagereader
    from roboscriptorium.clients.retry import patiently
    from roboscriptorium.config import Settings

    settings = Settings.from_env()
    model = settings.read_model
    OUT.mkdir(parents=True, exist_ok=True)
    path = _answers(model)
    answers = [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []
    done = {(a["book"], a["page"]) for a in answers if a["kinds"] is not None}
    rows = {}
    for path_rows in ROOT.glob("*--*.jsonl"):
        for x in path_rows.read_text().splitlines():
            r = json.loads(x)
            rows.setdefault((r["book"], r["page"]), []).append(r)
    todo = [k for k in sample() if k not in done][:limit]
    for n, (book, page) in enumerate(todo, 1):
        lines = sorted(rows[(book, page)], key=lambda r: r["line"])
        with pymupdf.open(Path("work") / book / "source.pdf") as doc:
            png = pagereader._render(doc[page - 1])
        listing = "\n".join(f"{i}. {r['state']['line']}" for i, r in enumerate(lines, 1))
        body = {
            "model": model, "prompt": (SHORT_PROMPT if SHORT else PROMPT).format(lines=listing),
            "stream": False,
            "think": False, "images": [base64.b64encode(png).decode()],
            "options": {"temperature": 0, "num_predict": 2000},
        }  # fmt: skip
        reply = patiently(
            lambda body=body: httpx.post(
                f"{settings.ollama_url}/api/generate", json=body, timeout=900
            )
        ).json()["response"]
        found = re.findall(r"\{[^{}]*\}", reply)
        try:
            kinds = json.loads(found[-1]) if found else None
        except json.JSONDecodeError:
            kinds = None
        if SHORT and kinds is not None:
            kinds = _kinds(kinds, len(lines))
        with _answers(model).open("a") as f:
            f.write(json.dumps({"book": book, "page": page, "reply": reply, "kinds": kinds,
                                "lines": [r["line"] for r in lines]}) + "\n")  # fmt: skip
        print(f"{n}/{len(todo)} {book[:30]} p{page}", flush=True)


def score() -> None:
    from laya_roles_eval import pipeline_roles

    from roboscriptorium import bench
    from roboscriptorium.config import Settings

    model = Settings.from_env().read_model
    last = {}
    for a in map(json.loads, _answers(model).read_text().splitlines()):
        last[(a["book"], a["page"])] = a
    gold = {}
    for path in ROOT.glob("*--*.jsonl"):
        for x in path.read_text().splitlines():
            r = json.loads(x)
            gold[(r["book"], r["page"], r["line"])] = r["gold"]["role"]
    ours = {}
    for spec in bench.SETS["tuning"]:
        name = spec.split(":")[0]
        if any(b == name for b, _ in last):
            ours.update({(name, *k): v for k, v in pipeline_roles(spec).items()})
    c: Counter = Counter()
    for (book, page), a in last.items():
        if a["kinds"] is None:
            c["unparsed pages"] += 1
            continue
        for i, line in enumerate(a["lines"], 1):
            g = gold[(book, page, line)]
            m = KINDS.get(str(a["kinds"].get(str(i), "")).upper()[:1], "body")
            o = ours.get((book, page, line))
            c["lines"] += 1
            c["ours wrong"] += o != g
            c["model wrong"] += m != g
            c["model fixes"] += m == g and o != g
            c["model breaks"] += o == g and m != g
            if g == "heading":
                c["headings"] += 1
                c["ours found"] += o == "heading"
                c["model found"] += m == "heading"
            elif m == "heading":
                c["model spurious headings"] += 1
            if o == g and m != g:
                print(f"  breaks {book[:24]} p{page} l{line}: {g} → {m}")
    print(dict(c))


if __name__ == "__main__":
    if sys.argv[1] == "ask":
        args = [a for a in sys.argv[2:] if not a.startswith("--")]
        ask(int(args[0]) if args else None)
    else:
        score()
