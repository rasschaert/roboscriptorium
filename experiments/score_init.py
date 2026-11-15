"""Every field `init` drafts, scored on the golden books, through `init`'s own code: the text
proper's two ends (against `tryouts/page-kinds-v1.json` where labelled), the language, and the
title, author and translator against the publisher's e-book of the pair (its `dc:title`, its
creators as author and translator). Run again after each change to `init`.

Page kinds are cached as `init` caches them (`stages/page-kinds.json`); the read model's
title-page answers in work/probes/init-score/<book>.json, keyed by the model. `--dry` checks
every input and asks nothing.

    uv run python experiments/score_init.py [--dry] [book …]
"""

import json
import re
import sys
import tomllib
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path

from roboscriptorium import bookinit, pagekinds
from roboscriptorium.clients import decide
from roboscriptorium.config import Settings
from roboscriptorium.files import write_atomic
from roboscriptorium.pdf import cached_text_layer

CACHE = Path("work/probes/init-score")
PUBLISHER = Path("work/.cache/publisher")
LABELS = json.loads(Path("tryouts/page-kinds-v1.json").read_text())["books"]


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in text if not unicodedata.combining(c))).strip()


def reference(epub: Path) -> dict[str, str]:
    """Title, author and translator as the publisher's e-book's metadata names them."""
    with zipfile.ZipFile(epub) as z:
        opf = z.read(next(n for n in z.namelist() if n.endswith(".opf"))).decode("utf-8", "replace")
    title = re.search(r"<dc:title[^>]*>([^<]*)</dc:title>", opf)
    roles = {m[0]: m[1] for m in re.findall(r'<meta[^>]*refines="#([^"]+)"[^>]*property="role"[^>]*>([^<]*)<', opf)}
    people = {"aut": [], "trl": []}
    for attrs, name in re.findall(r"<dc:(?:creator|contributor)([^>]*)>([^<]*)</dc:", opf):
        role = re.search(r'opf:role="([^"]+)"', attrs)
        ident = re.search(r'id="([^"]+)"', attrs)
        role = role[1] if role else roles.get(ident[1] if ident else "", "aut" if "creator" in attrs or not attrs else "")
        if role in people:
            people[role].append(name.strip())
    return {"title": title[1].strip() if title else "", "author": " & ".join(people["aut"]), "translator": " & ".join(people["trl"])}


def books(wanted: list[str]) -> list[tuple[str, Path, str]]:
    out = []
    for toml in sorted(Path("work").glob("*/book.toml")):
        golden = tomllib.loads(toml.read_text()).get("golden")
        name = toml.parent.name
        if golden and (not wanted or name in wanted):
            out.append((name, toml.parent, golden))
    return out


def main():
    dry = "--dry" in sys.argv
    wanted = [a for a in sys.argv[1:] if not a.startswith("--")]
    settings = Settings.from_env()
    todo, missing = [], []
    for name, root, golden in books(wanted):
        epub = PUBLISHER / f"{golden}.epub"
        lacks = [str(p) for p in (root / "source.pdf", root / "stages" / "textlayer.json", epub) if not p.exists()]
        (missing if lacks else todo).append((name, root, epub, lacks))
    for name, _, _, lacks in missing:
        print(f"{name}: left out, lacks {', '.join(lacks)}")
    if dry:
        print(f"{len(todo)} books ready, {len(missing)} left out; read model {settings.read_model}, page kinds {settings.role_model}")
        return
    client = decide.for_model(settings.role_model, settings.ollama_url)
    CACHE.mkdir(parents=True, exist_ok=True)
    right, seen = Counter(), Counter()
    for name, root, epub, _ in todo:
        pages = cached_text_layer(root / "source.pdf", root / "stages" / "textlayer.json")
        kinds = pagekinds.kinds(root / "source.pdf", pages, client, root / "stages" / "page-kinds.json")
        d = bookinit.draft(name, pages, kinds)
        held = CACHE / f"{name}.json"
        answers = json.loads(held.read_text()) if held.exists() else {}
        if settings.read_model not in answers:
            answers[settings.read_model] = bookinit.read_front(root / "source.pdf", kinds, settings.read_model, settings.ollama_url)
            write_atomic(held, json.dumps(answers, ensure_ascii=False))
        front = answers[settings.read_model]
        want = reference(epub)
        line = []
        for key in ("title", "author", "translator"):
            seen[key] += 1
            ok = fold(front.get(key, "")) == fold(want[key])
            right[key] += ok
            if not ok:
                line.append(f"{key} {front.get(key, '')!r} / e-book {want[key]!r}")
        language = tomllib.loads((root / "book.toml").read_text())["language"]
        seen["language"] += 1
        right["language"] += d.language[:2] == language[:2]
        if name in LABELS:
            labelled = {int(k): v for k, v in LABELS[name]["pages"].items()}
            ends = pagekinds.ends({p.number: labelled.get(p.number, "text") for p in pages})
            for end, got, w in (("first end", d.first, ends[0]), ("last end", d.last, ends[1])):
                seen[end] += 1
                right[end] += got == w
                if got != w:
                    line.append(f"{end} {got} / labelled {w}")
        print(f"{name[:40]:40} " + ("; ".join(line) or "all right"), flush=True)
    print("right:", {k: f"{right[k]} of {seen[k]}" for k in seen})


if __name__ == "__main__":
    main()
