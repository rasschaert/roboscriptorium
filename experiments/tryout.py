"""Try a model for a role on a frozen, versioned set, against the model that has the role.

A quick screen before the bench: a candidate that loses here isn't wired in; one that
wins goes on to a trust-data rebuild, a retrain and `bench`. Roles: reader, judge.

    uv run python experiments/tryout.py build reader      # freeze the set (no models)
    uv run python experiments/tryout.py run reader <model> [--glm]
    uv run python experiments/tryout.py build judge       # from cached suspects
    uv run python experiments/tryout.py run judge <model>

The reader set (`READER_VERSION`) holds body lines of the tuning books' bench slices,
each line's crop cut as the OCR check cuts it and saved as a PNG, and its printed text
from the aligned golden reference. Two strata per book: lines the text layer reads
wrong (the hard ones, up to `HARD` a book) and lines it reads right (`CONTROL` a book,
a candidate must not break them). The manifest in git (tryouts/reader-v<N>.json) holds
only ids and hashes; crops, texts and readings stay in work/tryout/.

The judge set (`JUDGE_VERSION`) holds the vision judge's questions about settled OCR
suspects of the tuning books' bench slices (the trust data's labels): the state, the
question and the crop exactly as the pipeline asks them, captured from a cached build.
Two strata per book: suspects the judge in use gets wrong (`JUDGE_HARD` a book) and
right (`JUDGE_CONTROL`). Each book's share of wrong picks is kept, so the score can be
weighted back to how often the judge in use errs.

A set never changes under its version: a different selection is a new version, and
every result names the version it was scored on, in tryouts/results.jsonl.
"""

import base64
import hashlib
import json
import random
import statistics
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pymupdf
from rapidfuzz.distance import Levenshtein

from roboscriptorium import bench, disagreements, ocrcheck, pipeline
from roboscriptorium.book import Book
from roboscriptorium.cli import _verdicts
from roboscriptorium.config import Settings
from roboscriptorium.golden.align import align
from roboscriptorium.golden.manifest import Golden
from roboscriptorium.golden.reference import load_chapters
from roboscriptorium.pdf import cached_text_layer
from roboscriptorium.reflow import HYPHENS

sys.path.insert(0, str(Path(__file__).parent))
from ocr_trust_data import fold  # noqa: E402  the trust data's labels compare lines the same way

READER_VERSION = 1
HARD, CONTROL = 30, 20
JUDGE_VERSION = 1
JUDGE_HARD, JUDGE_CONTROL = 25, 25
SEED = 0
QUOTES = "'\"‘’“”‚„«»"
WORK = Path("work/tryout")
GIT = Path("tryouts")


def sha(data: bytes | str) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()[:16]


def slice_of(spec: str) -> tuple[Book, tuple[int, int], tuple[int, int] | None]:
    name, *rest = spec.split(":")
    book = Book.load(Path("work") / name)
    pages = tuple(map(int, rest[0].split("-"))) if rest and rest[0] else book.body_pages
    chapters = tuple(map(int, rest[1].split("-"))) if len(rest) > 1 and rest[1] else None
    return book, pages, chapters


def build_reader() -> None:
    root = WORK / f"reader-v{READER_VERSION}"
    manifest_path = GIT / f"reader-v{READER_VERSION}.json"
    if manifest_path.exists():
        sys.exit(f"{manifest_path} exists: a set never changes; bump READER_VERSION")
    (root / "crops").mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    items, books = [], {}
    for spec in bench.SETS["tuning"]:
        book, (first, last), chapters = slice_of(spec)
        pages = [
            p
            for p in cached_text_layer(book.source, book.stages / "textlayer.json")
            if first <= p.number <= last
        ]
        reference = load_chapters(Golden.load(book.golden).text_dir)
        if chapters:
            reference = reference[chapters[0] - 1 : chapters[1]]
        reference, _ = disagreements.patch(reference, _verdicts(book))
        labels = align(pages, reference)
        by_number = {p.number: p for p in pages}
        body = [
            (ref, lab.truth)
            for ref, lab in labels.items()
            if lab.role == "body" and lab.truth and by_number[ref.page].lines[ref.line].text.strip()
        ]
        line = {ref: by_number[ref.page].lines[ref.line].text for ref, _ in body}
        # The aligner gives a word broken over two lines to one of them, so neither
        # line's truth is what its crop shows.
        body = [
            (r, t)
            for r, t in body
            if not _beside_break(by_number[r.page].lines, r.line) and not _shifted(line[r], t)
        ]
        hard = [(r, t) for r, t in body if fold(line[r]) != fold(t)]
        control = [(r, t) for r, t in body if fold(line[r]) == fold(t)]
        chosen = [("hard", x) for x in rng.sample(hard, min(HARD, len(hard)))]
        chosen += [("control", x) for x in rng.sample(control, min(CONTROL, len(control)))]
        prompt = pipeline.read_prompt(
            book, pages, pipeline.dash_style(book, pages), pipeline.ellipsis_style(book, pages)
        )
        books[book.root.name] = {"spec": spec, "prompt": prompt, "prompt_sha": sha(prompt)}
        with pymupdf.open(book.source) as doc:
            for stratum, (ref, truth) in sorted(chosen, key=lambda x: (x[1][0].page, x[1][0].line)):
                page = by_number[ref.page]
                boxes = ocrcheck.line_boxes(doc[ref.page - 1], page)
                box = boxes[ref.line]
                span = ocrcheck.crop_span(boxes, ref.line)
                png = ocrcheck._line_crop(doc, ref.page, box, span)
                item_id = f"{book.root.name}:{ref.page}:{ref.line}"
                (root / "crops" / f"{sha(item_id)}.png").write_bytes(png)
                items.append(
                    {
                        "id": item_id,
                        "book": book.root.name,
                        "stratum": stratum,
                        "layer": line[ref],
                        "truth": truth,
                        "crop": sha(png),
                        "truth_sha": sha(truth),
                        "cache_key": ocrcheck.line_key(page, boxes, ref.line),
                    }
                )
        print(f"{book.root.name}: {sum(i['book'] == book.root.name for i in items)} lines")
    (root / "items.json").write_text(
        json.dumps({"books": books, "items": items}, ensure_ascii=False)
    )
    GIT.mkdir(exist_ok=True)
    manifest = {
        "role": "reader",
        "version": READER_VERSION,
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": _commit(),
        "strata": {"hard": HARD, "control": CONTROL, "seed": SEED},
        "books": {n: {"spec": b["spec"], "prompt_sha": b["prompt_sha"]} for n, b in books.items()},
        "items": [{k: i[k] for k in ("id", "stratum", "crop", "truth_sha")} for i in items],
    }
    manifest_path.write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"{len(items)} lines; manifest {manifest_path}")


def _beside_break(lines, k: int) -> bool:
    return lines[k].text.rstrip().endswith(HYPHENS) or (
        k > 0 and lines[k - 1].text.rstrip().endswith(HYPHENS)
    )


def _letters(word: str) -> str:
    return "".join(c for c in word if c.isalnum())


def _shifted(layer: str, truth: str) -> bool:
    """Whether the aligner moved letters across the line's ends: a word with letters
    gained or lost at either end, or an end word one is the other's prefix or suffix of
    ("raadslaagden" for "beraadslaagden", "week" for "week—if"). A closing quote or a
    dash at the end has no letters, so it stays."""
    a = [w for w in fold(layer).split() if _letters(w)]
    b = [w for w in fold(truth).split() if _letters(w)]
    if not a or not b:
        return True
    for x, y in ((a, b), (a[::-1], b[::-1])):
        if len(x) != len(y) and (_letters(x[0]) != _letters(y[0])):
            return True
    first = (_letters(a[0]), _letters(b[0]))
    last = (_letters(a[-1]), _letters(b[-1]))
    return any(
        p != q and len(p) != len(q) and (p.endswith(q) or q.endswith(p)) and min(len(p), len(q)) > 0
        for p, q in [first]
    ) or any(
        p != q
        and len(p) != len(q)
        and (p.startswith(q) or q.startswith(p))
        and min(len(p), len(q)) > 0
        for p, q in [last]
    )


def _commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True
    ).stdout.strip()


def load_set() -> tuple[dict, list[dict]]:
    root = WORK / f"reader-v{READER_VERSION}"
    data = json.loads((root / "items.json").read_text())
    manifest = json.loads((GIT / f"reader-v{READER_VERSION}.json").read_text())
    want = {i["id"]: i for i in manifest["items"]}
    for item in data["items"]:
        png = (root / "crops" / f"{sha(item['id'])}.png").read_bytes()
        m = want[item["id"]]
        if sha(png) != m["crop"] or sha(item["truth"]) != m["truth_sha"]:
            sys.exit(f"{item['id']} differs from the manifest: the set changed under its version")
        item["png"] = png
    return data["books"], data["items"]


def stage_readings(items: list[dict], stage: str, prompt_of=None) -> dict[str, tuple[str, str]]:
    """The book caches' readings of these exact crops, per item id: (text, via)."""
    out = {}
    for name in {i["book"] for i in items}:
        path = Path("work") / name / "stages" / stage
        if not path.exists():
            continue
        raw = json.loads(path.read_text())
        if prompt_of and raw.get("prompt") != prompt_of(name):
            continue
        via = {k for keys in raw.get("via", {}).values() for k in keys}
        for i in items:
            if i["book"] == name and i["cache_key"] in raw["lines"]:
                out[i["id"]] = (
                    raw["lines"][i["cache_key"]],
                    "hosted" if i["cache_key"] in via else "",
                )
    return out


def _readings_path(model: str) -> Path:
    name = model.replace(":", "_").replace("/", "_")
    return WORK / f"reader-v{READER_VERSION}" / "readings" / f"{name}.json"


def read_all(model: str, items: list[dict], books: dict) -> dict[str, str]:
    """`model`'s reading of every item, as the pipeline would ask it (glm-ocr without a
    prompt, any other model told the book's style), cached per set and model."""
    cache = _readings_path(model)
    done = json.loads(cache.read_text()) if cache.exists() else {}
    settings = Settings.from_env()
    todo = [i for i in items if i["id"] not in done]
    for n, i in enumerate(todo, 1):
        if model.startswith("glm-ocr"):
            text = ocrcheck.read_line(i["png"], model, settings.ollama_url)
        else:
            text = ocrcheck.transcribe(
                i["png"], model, settings.ollama_url, books[i["book"]]["prompt"]
            )
        done[i["id"]] = text
        if n % 25 == 0 or n == len(todo):
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(done, ensure_ascii=False))
            print(f"  {model}: {n}/{len(todo)}", flush=True)
    return done


def quotes_differ(a: str, b: str) -> bool:
    return Counter(c for c in a if c in QUOTES) != Counter(c for c in b if c in QUOTES)


def score(name: str, reading: dict[str, str], items: list[dict], others: dict[str, dict]) -> dict:
    def right(i, text):
        return fold(text) == fold(i["truth"])

    out: dict = {"model": name}
    for stratum in ("hard", "control"):
        group = [i for i in items if i["stratum"] == stratum]
        chars = sum(len(fold(i["truth"])) for i in group)
        edits = sum(Levenshtein.distance(fold(reading[i["id"]]), fold(i["truth"])) for i in group)
        out[stratum] = {
            "lines": len(group),
            "right": sum(right(i, reading[i["id"]]) for i in group),
            "cer": round(edits / max(1, chars), 5),
            "quote_lines_wrong": sum(quotes_differ(reading[i["id"]], i["truth"]) for i in group),
        }
    wrong = {i["id"] for i in items if not right(i, reading[i["id"]])}
    out["shared_errors"] = {
        other: len(wrong & {i["id"] for i in items if not right(i, r[i["id"]])})
        for other, r in others.items()
    }
    out["only_right_on"] = sum(
        i["stratum"] == "hard"
        and right(i, reading[i["id"]])
        and not any(right(i, r[i["id"]]) for r in others.values())
        for i in items
    )
    return out


def run_reader(model: str) -> None:
    books, items = load_set()
    settings = Settings.from_env()
    incumbents: dict[str, dict[str, str]] = {}
    for label, stage, prompt_of in (
        (settings.read_model, "third-reading.json", lambda n: books[n]["prompt"]),
        (settings.ocr_model, "second-reading.json", None),
    ):
        seeded = stage_readings(items, stage, prompt_of)
        cache = _readings_path(label)
        cache.parent.mkdir(parents=True, exist_ok=True)
        done = json.loads(cache.read_text()) if cache.exists() else {}
        # Hosted readings stand for the local model in the books, not in its score here.
        local = {k: t for k, (t, via) in seeded.items() if not via}
        done.update({k: t for k, t in local.items() if k not in done})
        cache.write_text(json.dumps(done, ensure_ascii=False))
        hosted = len(seeded) - len(local)
        print(f"{label}: {len(local)} of {len(items)} from the book caches ({hosted} hosted, read again)")
        incumbents[label] = read_all(label, items, books)
    candidate = read_all(model, items, books)
    layer = {i["id"]: i["layer"] for i in items}
    rows = [score("text layer", layer, items, incumbents)]
    rows += [
        score(n, r, items, {k: v for k, v in incumbents.items() if k != n})
        for n, r in incumbents.items()
    ]
    if model not in incumbents:
        rows.append(score(model, candidate, items, incumbents))
    print(f"\nreader set v{READER_VERSION}: {len(items)} lines from {len(books)} books")
    print(
        f"{'model':32} {'hard right':>10} {'hard CER':>9} {'control right':>13} {'ctrl CER':>9} {'quotes wrong h/c':>17} {'only right':>10}"
    )
    for r in rows:
        h, c = r["hard"], r["control"]
        print(
            f"{r['model'][:32]:32} {h['right']:>4}/{h['lines']:<5} {h['cer']:>9.2%} {c['right']:>6}/{c['lines']:<6} "
            f"{c['cer']:>9.2%} {h['quote_lines_wrong']:>8}/{c['quote_lines_wrong']:<8} {r['only_right_on']:>10}"
        )
    for r in rows[1:]:
        print(f"  {r['model']}: errors shared with {r['shared_errors']}")
    result = {
        "date": datetime.now(UTC).isoformat(timespec="seconds"),
        "role": "reader",
        "set_version": READER_VERSION,
        "commit": _commit(),
        "candidate": model,
        "digests": _digests([model, *incumbents]),
        "rows": rows,
    }
    with (GIT / "results.jsonl").open("a") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")


def _digests(models: list[str]) -> dict[str, str]:
    """Each Ollama model's digest, so a result says which build of a tag it scored."""
    tags = httpx.get(f"{Settings.from_env().ollama_url}/api/tags", timeout=30).json()["models"]
    digests = {t["name"]: t["digest"][:12] for t in tags}
    return {m: digests.get(m, "") for m in models}


def build_judge() -> None:
    import ocr_trust_data

    root = WORK / f"judge-v{JUDGE_VERSION}"
    manifest_path = GIT / f"judge-v{JUDGE_VERSION}.json"
    if manifest_path.exists():
        sys.exit(f"{manifest_path} exists: a set never changes; bump JUDGE_VERSION")
    (root / "crops").mkdir(parents=True, exist_ok=True)
    settings = Settings.from_env()
    asked = {}  # (page, line, versions) -> (state, questions, png, answer)
    real_ask = ocrcheck._ask

    def capture(client, cache, state, questions, image=None):
        answer = real_ask(client, cache, state, questions, image)
        if client.model == settings.judge_model and image is not None:
            asked[(state["page"], state["line"], tuple(state["readings"]))] = (
                state, questions, image(), answer,
            )  # fmt: skip
        return answer

    ocrcheck._ask = capture
    rng = random.Random(SEED)
    items, books = [], {}
    letters = "abcdefg"
    for spec in bench.SETS["tuning"]:
        name, *rest = spec.split(":")
        asked.clear()
        rows = ocr_trust_data.build(name, ":".join(rest))
        hard, control = [], []
        for row in rows:
            s = row["suspect"]
            key = (s["page"], s["line"], (s["ours"], *s["others"]))
            if not row["settled"] or key not in asked:
                continue
            value = asked[key][3]["value"]
            right = value in letters and row["right"][letters.index(value)]
            (control if right else hard).append((row, asked[key]))
        books[name] = {"spec": spec, "settled": len(hard) + len(control), "wrong": len(hard)}
        chosen = [("hard", x) for x in rng.sample(hard, min(JUDGE_HARD, len(hard)))]
        chosen += [("control", x) for x in rng.sample(control, min(JUDGE_CONTROL, len(control)))]
        for stratum, (row, (state, questions, png, answer)) in chosen:
            s = row["suspect"]
            item_id = f"{name}:{s['page']}:{s['line']}:{s['start']}"
            (root / "crops" / f"{sha(item_id)}.png").write_bytes(png)
            items.append(
                {
                    "id": item_id,
                    "book": name,
                    "stratum": stratum,
                    "state": state,
                    "questions": questions,
                    "right": row["right"],
                    "incumbent": answer,
                    "crop": sha(png),
                    "question_sha": sha(json.dumps([state, questions], sort_keys=True)),
                }
            )
        print(f"{name}: {len(hard)} wrong of {books[name]['settled']} settled; {len(chosen)} kept")
    (root / "items.json").write_text(
        json.dumps({"books": books, "items": items}, ensure_ascii=False)
    )
    GIT.mkdir(exist_ok=True)
    manifest = {
        "role": "judge",
        "version": JUDGE_VERSION,
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": _commit(),
        "incumbent": settings.judge_model,
        "strata": {"hard": JUDGE_HARD, "control": JUDGE_CONTROL, "seed": SEED},
        "books": books,
        "items": [{k: i[k] for k in ("id", "stratum", "crop", "question_sha")} for i in items],
    }
    manifest_path.write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"{len(items)} suspects; manifest {manifest_path}")


def load_judge_set() -> tuple[dict, list[dict]]:
    """The set's manifest and its items, each checked against the manifest."""
    root = WORK / f"judge-v{JUDGE_VERSION}"
    data = json.loads((root / "items.json").read_text())
    manifest = json.loads((GIT / f"judge-v{JUDGE_VERSION}.json").read_text())
    want = {i["id"]: i for i in manifest["items"]}
    for item in data["items"]:
        png = (root / "crops" / f"{sha(item['id'])}.png").read_bytes()
        m = want[item["id"]]
        question = sha(json.dumps([item["state"], item["questions"]], sort_keys=True))
        if sha(png) != m["crop"] or question != m["question_sha"]:
            sys.exit(f"{item['id']} differs from the manifest: the set changed under its version")
        item["png"] = png
    return manifest, data["items"]


def run_judge(model: str) -> None:
    from roboscriptorium.clients import decide

    manifest, items = load_judge_set()
    books = manifest["books"]
    settings = Settings.from_env()
    cache = (
        WORK
        / f"judge-v{JUDGE_VERSION}"
        / "answers"
        / f"{model.replace(':', '_').replace('/', '_')}.json"
    )
    cache.parent.mkdir(parents=True, exist_ok=True)
    done = json.loads(cache.read_text()) if cache.exists() else {}
    if model.startswith("llama:"):
        # llama:<model>@<port>: a decision model with a readout on llama-server.
        from roboscriptorium.clients import llama

        name, port = model.removeprefix("llama:").split("@")
        client = llama.ReadoutClient(name, f"http://127.0.0.1:{port}")
    else:
        client = decide.for_model(model, settings.ollama_url)
    todo = [i for i in items if i["id"] not in done]
    seconds = []
    for n, i in enumerate(todo, 1):
        start = datetime.now(UTC)
        a = client.decide(i["state"], i["questions"], image_png=i["png"])["reading"]
        seconds.append((datetime.now(UTC) - start).total_seconds())
        done[i["id"]] = {"value": a.value, "confidence": a.confidence}
        if n % 25 == 0 or n == len(todo):
            cache.write_text(json.dumps(done))
            print(f"{n}/{len(todo)}", flush=True)
    incumbent = {i["id"]: i["incumbent"] for i in items}
    rows = [_judge_score(f"{model} (candidate)", done, items, books)]
    rows.append(_judge_score(f"{manifest['incumbent']} (in use)", incumbent, items, books))
    for r in rows:
        print(
            f"{r['name']:40} hard {r['hard']:>3}/{r['hard_n']}  control {r['control']:>3}/"
            f"{r['control_n']}  weighted {r['weighted']:.1%}  sure-and-wrong {r['sure_wrong']}"
        )
    if seconds:
        print(f"{statistics.median(seconds):.2f} s a question (median of {len(seconds)})")
    result = {
        "role": "judge",
        "set_version": JUDGE_VERSION,
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": _commit(),
        "candidate": model,
        "digests": _digests([model]) if not model.startswith("llama:") else {},
        "seconds": statistics.median(seconds) if seconds else None,
        "rows": rows,
    }
    with (GIT / "results.jsonl").open("a") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")


def _judge_score(name: str, answers: dict, items: list[dict], books: dict) -> dict:
    """Right per stratum, and right weighted back to each book's real share of the judge
    in use's errors, books weighing the same; "sure and wrong": wrong at confidence >= 0.8."""
    letters = "abcdefg"

    def right(i):
        v = answers[i["id"]]["value"]
        return v in letters and i["right"][letters.index(v)]

    out = {"name": name, "sure_wrong": 0}
    for stratum in ("hard", "control"):
        these = [i for i in items if i["stratum"] == stratum]
        out[stratum] = sum(right(i) for i in these)
        out[f"{stratum}_n"] = len(these)
    out["sure_wrong"] = sum(not right(i) and answers[i["id"]]["confidence"] >= 0.8 for i in items)
    per_book = []
    for book, b in books.items():
        share = b["wrong"] / b["settled"] if b["settled"] else 0
        acc = {}
        for stratum in ("hard", "control"):
            these = [i for i in items if i["book"] == book and i["stratum"] == stratum]
            acc[stratum] = sum(right(i) for i in these) / len(these) if these else None
        if acc["hard"] is None or acc["control"] is None:
            continue
        per_book.append(share * acc["hard"] + (1 - share) * acc["control"])
    out["weighted"] = sum(per_book) / len(per_book) if per_book else 0.0
    return out


if __name__ == "__main__":
    command, role = sys.argv[1], sys.argv[2]
    if role not in ("reader", "judge"):
        sys.exit("roles: reader, judge")
    if command == "build":
        build_reader() if role == "reader" else build_judge()
    elif command == "run":
        run_reader(sys.argv[3]) if role == "reader" else run_judge(sys.argv[3])
