"""Probe: the recall of `probe_translation_check.py`. A copy of Stella's build with one
planted reading error in each of up to 48 paragraphs the check passed clean, and the truth
(paragraph, kind, planted text, the print's).

    uv run python experiments/edition_recall_plant.py <planted.epub> <truth.jsonl>
"""

import html
import json
import random
import re
import sys
import zipfile

sys.path.insert(0, "experiments")
from pathlib import Path

import probe_translation_check as p

SRC, OUT = Path("work/stella/stella.epub"), Path(sys.argv[1])
truth_path = Path(sys.argv[2])
flags = {
    json.loads(l)["paragraph"]: json.loads(l)["flags"]
    for l in open("work/probes/stella-editions/full-hosted.jsonl")
}
ps = p.paragraphs(SRC)
rng = random.Random(7)
pool = [k for k, t in enumerate(ps) if len(t) > 300 and not flags.get(k + 1) and (k + 1) in flags]
rng.shuffle(pool)
print(len(pool), "paragraphs to plant in")
LETTERS = [
    ("ij", "y"),
    ("f", "t"),
    ("s", "z"),
    ("o", "c"),
    ("e", "c"),
    ("n", "h"),
    ("b", "h"),
    ("n", "r"),
]
REAL = [
    ("hij", "bij"),
    ("had", "bad"),
    ("ben", "hen"),
    ("kon", "kou"),
    ("hem", "bem"),
    ("dan", "dat"),
]


def words(t):
    return [m for m in re.finditer(r"\b[a-zA-Zëéèïöü]+\b", t)]


def plant(kind, t):
    ws = words(t)
    if kind == "letters":
        rng.shuffle(LETTERS)
        for a, b in LETTERS:
            c = [m for m in ws if len(m[0]) > 4 and a in m[0][1:]]
            if c:
                m = rng.choice(c)
                w = m[0]
                i = w.index(a, 1)
                return m[0], w[:i] + b + w[i + len(a) :]
    if kind == "real":
        for a, b in rng.sample(REAL, len(REAL)):
            c = [m for m in ws if m[0] == a]
            if c:
                return a, b
    if kind == "glued":
        for _ in range(50):
            i = rng.randrange(len(ws) - 1)
            a, b = ws[i], ws[i + 1]
            if t[a.end() : b.start()] == " " and len(a[0]) > 2 and len(b[0]) > 2:
                return f"{a[0]} {b[0]}", a[0] + b[0]
    if kind == "split":
        c = [m for m in ws if len(m[0]) > 8]
        if c:
            w = rng.choice(c)[0]
            i = rng.randrange(3, len(w) - 3)
            return w, w[:i] + " " + w[i:]
    if kind == "dropped":
        for _ in range(50):
            i = rng.randrange(1, len(ws) - 1)
            a, b, c = ws[i - 1], ws[i], ws[i + 1]
            if len(b[0]) <= 4 and t[a.end() : b.start()] == " " and t[b.end() : c.start()] == " ":
                return f"{a[0]} {b[0]} {c[0]}", f"{a[0]} {c[0]}"
    if kind == "accent":
        c = [m for m in ws if re.search("[ëéèï]", m[0])]
        if c:
            w = rng.choice(c)[0]
            return w, w.translate(str.maketrans("ëéèï", "eeei"))
    return None


kinds = ["letters", "real", "glued", "split", "dropped", "accent"] * 8
z = zipfile.ZipFile(SRC)
files = {n: z.read(n) for n in z.namelist()}
truth = []
for kind in kinds:
    placed = False
    while pool and not placed:
        k = pool.pop()
        for _ in range(10):
            got = plant(kind, ps[k])
            if not got:
                continue
            old, new = got
            # Only where the text sits in its own <p> unbroken by markup, once there.
            pat = r"(?<![\wëéèïöü])" + re.escape(old) + r"(?![\wëéèïöü])"
            name = "OEBPS/text-001.xhtml"
            raw = files[name].decode()
            spans = [
                m
                for m in re.finditer(r"<p\b[^>]*>(.*?)</p>", raw, re.S)
                if html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m[1]))).strip()
            ]
            inner = spans[k]
            if len(re.findall(pat, inner[1])) != 1:
                continue
            a, b = inner.span(1)
            files[name] = (raw[:a] + re.sub(pat, new, inner[1]) + raw[b:]).encode()
            truth.append({"paragraph": k + 1, "kind": kind, "planted": new, "print": old})
            placed = True
            break
with zipfile.ZipFile(OUT, "w") as o:
    for n in z.namelist():
        o.writestr(z.getinfo(n), files[n])
truth_path.write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in truth))
print(len(truth), "planted;", {k: sum(t["kind"] == k for t in truth) for k in set(kinds)})
print(",".join(str(t["paragraph"]) for t in sorted(truth, key=lambda t: t["paragraph"])))
