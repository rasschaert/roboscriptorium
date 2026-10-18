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
out.jsonl per paragraph, so a rerun skips the done ones. Local only: the editions are
copyrighted.
"""

import argparse
import html
import json
import re
import sys
import time
import zipfile
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


def align(a: list[str], b: list[str]) -> dict[int, list[int]]:
    """For each paragraph of `b`, the paragraphs of `a` it corresponds to, by lengths."""
    def share(ps):
        t = sum(len(p) for p in ps)
        return [len(p) / t for p in ps]

    A, B = share(a), share(b)
    n, m = len(A), len(B)
    inf = float("inf")
    cost = [[inf] * (m + 1) for _ in range(n + 1)]
    back = {}
    cost[0][0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            if cost[i][j] == inf:
                continue
            for di, dj, pen in ((1, 1, 0), (1, 2, 0.002), (2, 1, 0.002)):
                if i + di <= n and j + dj <= m:
                    d = cost[i][j] + abs(sum(A[i : i + di]) - sum(B[j : j + dj])) + pen
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("built")
    ap.add_argument("out")
    ap.add_argument("editions", nargs="+")
    ap.add_argument("--paragraphs", default="")
    ap.add_argument("--model", default="qwen3.8:27b-nvfp4")
    args = ap.parse_args()
    nl = paragraphs(Path(args.built))
    others = [edition(s) for s in args.editions]
    maps = [(name, ps, align(ps, nl)) for name, ps in others]
    want = [int(x) - 1 for x in args.paragraphs.split(",") if x] or range(len(nl))
    out = Path(args.out)
    done = {json.loads(line)["paragraph"] for line in out.open()} if out.exists() else set()
    url = Settings.from_env().ollama_url
    with httpx.Client(base_url=url, timeout=900) as http:
        for j in want:
            if j + 1 in done:
                continue
            texts = "\n\n".join(
                f"{name}:\n" + "\n".join(ps[i] for i in m.get(j, [])) for name, ps, m in maps
            )
            t0 = time.time()
            r = http.post(
                "/api/chat",
                json={
                    "model": args.model,
                    "stream": False,
                    "think": True,
                    "format": SCHEMA,
                    "messages": [
                        {"role": "user", "content": PROMPT.format(dutch=nl[j], others=texts)}
                    ],
                    "options": {"temperature": 0},
                },
            )
            r.raise_for_status()
            flags = json.loads(r.json()["message"]["content"])["flags"]
            row = {"paragraph": j + 1, "seconds": round(time.time() - t0), "flags": flags}
            with out.open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"¶{j + 1}: {len(flags)} flags in {row['seconds']} s", flush=True)
            for fl in flags:
                print(f"   {fl['dutch']!r} → {fl['fix']!r} ({fl['evidence'][:80]})", flush=True)


if __name__ == "__main__":
    sys.exit(main())
