"""Probe: errors in a built Dutch book found against its original and another translation.

Not a pipeline stage: an instrument for a book with no reference (Stella). The build's
paragraphs are aligned with each other edition's by length (1:1, 1:2, 2:1); a thinking
model then reads each Dutch paragraph beside its counterparts and lists what reads as a
reading error in the Dutch (a real word that makes no sense where the original says
otherwise, glued or split words, a lost or extra word), with the other editions'
evidence. Each flag is then checked by eye on a crop of the scan.

    uv run python experiments/probe_translation_check.py <built.epub> <out.jsonl> \\
        <edition.epub>:<first paragraph>:<last heading> … [--paragraphs 1,5,9] [--model m]

An edition's slice runs from the paragraph starting with <first paragraph> up to the
first paragraph starting with <last heading> (or the end). Flags are appended to
out.jsonl per paragraph, so a rerun skips the done ones. The editions are copyrighted:
`--via openrouter:<model>@<provider>` asks a hosted build only where the user allowed it
(the edition checks, 2026-10-18), eight at a time, its thinking capped.
"""

import argparse
import html
import json
import re
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from roboscriptorium.config import Settings


def paragraphs(path: Path) -> list[str]:
    """An EPUB's `p` texts in spine order."""
    z = zipfile.ZipFile(path)
    opf = next(n for n in z.namelist() if n.endswith(".opf"))
    o = z.read(opf).decode()
    items = {}
    for tag in re.findall(r"<item\b[^>]*>", o):
        i, h = re.search(r'id="([^"]+)"', tag), re.search(r'href="([^"]+)"', tag)
        if i and h:
            items[i[1]] = h[1]
    base = opf.rsplit("/", 1)[0] + "/" if "/" in opf else ""
    out = []
    for i in re.findall(r'itemref[^>]*idref="([^"]+)"', o):
        raw = z.read(base + items[i]).decode(errors="replace")
        for m in re.findall(r"<p\b[^>]*>(.*?)</p>", raw, re.S):
            t = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m))).strip()
            if t:
                out.append(t)
    return out


def edition(spec: str) -> tuple[str, list[str]]:
    path, first, last = (spec.split(":") + [""])[:3]
    ps = paragraphs(Path(path))
    s = next(k for k, t in enumerate(ps) if t.startswith(first))
    e = next((k for k in range(s + 1, len(ps)) if last and ps[k].startswith(last)), len(ps))
    return Path(path).stem, ps[s:e]


def anchors(p: str) -> set[str]:
    """What a translation carries over unchanged: numbers, and capitalised words not opening
    a sentence (names, places)."""
    numbers = set(re.findall(r"\d+", p))
    names = re.findall(r"(?<![.!?:»«“”‘’\"]\s)(?<!^)\b([A-ZÀ-Ý][\w’'-]{2,})", p)
    return numbers | set(names)


def align(a: list[str], b: list[str]) -> dict[int, list[int]]:
    """For each paragraph of `b`, the paragraphs of `a` it corresponds to, by lengths and
    shared names and numbers; a paragraph one edition has and the other lacks (a preface,
    a motto) maps to none."""

    def share(ps):
        t = sum(len(p) for p in ps)
        return [len(p) / t for p in ps]

    A, B = share(a), share(b)
    n, m = len(A), len(B)
    KA, KB = [anchors(p) for p in a], [anchors(p) for p in b]
    # Each name or number the two sides share lowers the cost as about half an average
    # paragraph's length would.
    bonus = 0.5 / max(n, m)
    inf = float("inf")
    cost = [[inf] * (m + 1) for _ in range(n + 1)]
    back = {}
    cost[0][0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            if cost[i][j] == inf:
                continue
            # A paragraph without a counterpart costs its whole length and a little more.
            for di, dj, pen in (
                (1, 1, 0),
                (1, 2, 0.002),
                (2, 1, 0.002),
                (1, 0, 0.004),
                (0, 1, 0.004),
            ):
                if i + di <= n and j + dj <= m:
                    d = cost[i][j] + abs(sum(A[i : i + di]) - sum(B[j : j + dj])) + pen
                    if di and dj:
                        shared = set().union(*KA[i : i + di]) & set().union(*KB[j : j + dj])
                        d -= bonus * min(len(shared), 4)
                    if d < cost[i + di][j + dj]:
                        cost[i + di][j + dj] = d
                        back[(i + di, j + dj)] = (i, j)
    out: dict[int, list[int]] = {}
    k = (n, m)
    while k != (0, 0):
        i, j = back[k]
        for jj in range(j, k[1]):
            out[jj] = list(range(i, k[0]))
        k = (i, j)
    return out


PROMPT = """The Dutch paragraph below comes from an OCR reading of a printed Dutch translation. \
Beside it are the same passage in the original and in another translation.

List every place where the Dutch text looks like a reading error: a word that is wrong or \
makes no sense where the other texts say otherwise (a misread letter giving another real \
word), words glued together or split apart, a missing or extra word, a wrong name or number. \
Do not list differences that are only the translator's choice of words or phrasing, nor \
punctuation or quote marks. If there is nothing, return an empty list.

For each, give "dutch": the exact text as it stands in the Dutch paragraph, "fix": what \
the Dutch should read, and "evidence": the words in the other texts that show it.

Dutch:
{dutch}

{others}"""

SCHEMA = {
    "type": "object",
    "properties": {
        "flags": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "dutch": {"type": "string"},
                    "fix": {"type": "string"},
                    "evidence": {"type": "string"},
                },
                "required": ["dutch", "fix", "evidence"],
            },
        }
    },
    "required": ["flags"],
}


def ask_local(http: httpx.Client, model: str, prompt: str) -> list[dict]:
    r = http.post(
        "/api/chat",
        json={
            "model": model,
            "stream": False,
            "think": True,
            "format": SCHEMA,
            "messages": [{"role": "user", "content": prompt}],
            "options": {"temperature": 0},
        },
    )
    r.raise_for_status()
    return json.loads(r.json()["message"]["content"])["flags"]


def ask_hosted(via: str, prompt: str) -> tuple[list[dict], float]:
    """The flags and what the call cost in dollars (OpenRouter's usage accounting)."""
    from roboscriptorium.clients import openrouter

    name, provider = openrouter.parse(via)
    strict = json.loads(json.dumps(SCHEMA))
    strict["additionalProperties"] = False
    strict["properties"]["flags"]["items"]["additionalProperties"] = False
    body = {
        "model": name,
        "temperature": 0,
        "messages": [{"role": "user", "content": prompt}],
        "reasoning": {"max_tokens": 3000},
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "flags", "strict": True, "schema": strict},
        },
        "provider": {**openrouter._routing(provider), "require_parameters": True},
        "usage": {"include": True},
    }
    r = openrouter._post(openrouter.URL, body, None)
    flags = json.loads(r["choices"][0]["message"]["content"])["flags"]
    return flags, float(r.get("usage", {}).get("cost") or 0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("built")
    ap.add_argument("out")
    ap.add_argument("editions", nargs="+")
    ap.add_argument("--paragraphs", default="")
    ap.add_argument("--model", default="qwen3.8:27b-nvfp4")
    ap.add_argument("--via", default="")
    # Dollars a hosted run may spend; no new call starts past it.
    ap.add_argument("--budget", type=float, default=0.0)
    args = ap.parse_args()
    nl = paragraphs(Path(args.built))
    others = [edition(s) for s in args.editions]
    maps = [(name, ps, align(ps, nl)) for name, ps in others]
    want = [int(x) - 1 for x in args.paragraphs.split(",") if x] or range(len(nl))
    out = Path(args.out)
    done = {json.loads(line)["paragraph"] for line in out.open()} if out.exists() else set()
    url = Settings.from_env().ollama_url
    todo = [j for j in want if j + 1 not in done]
    spent = [0.0]

    def one(j: int) -> dict | None:
        if args.budget and spent[0] >= args.budget:
            return None
        texts = "\n\n".join(
            f"{name}:\n" + "\n".join(ps[i] for i in m.get(j, [])) for name, ps, m in maps
        )
        prompt = PROMPT.format(dutch=nl[j], others=texts)
        t0 = time.time()
        cost = 0.0
        if args.via:
            try:
                flags, cost = ask_hosted(args.via, prompt)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 402:
                    spent[0] = float("inf")
                    print("payment required: the hosted run stops", flush=True)
                    return None
                raise
            spent[0] += cost
        else:
            with httpx.Client(base_url=url, timeout=900) as http:
                flags = ask_local(http, args.model, prompt)
        seconds = round(time.time() - t0)
        return {"paragraph": j + 1, "seconds": seconds, "cost": cost, "flags": flags}

    with ThreadPoolExecutor(8 if args.via else 1) as pool:
        for row in pool.map(one, todo):
            if row is None:
                continue
            with out.open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n, sec = len(row["flags"]), row["seconds"]
            print(f"¶{row['paragraph']}: {n} flags in {sec} s, ${spent[0]:.3f} so far", flush=True)
            for fl in row["flags"]:
                print(f"   {fl['dutch']!r} → {fl['fix']!r} ({fl['evidence'][:80]})", flush=True)


if __name__ == "__main__":
    sys.exit(main())
