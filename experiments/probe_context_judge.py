"""Probe: a context judge. Does a thinking model that reads the text around an OCR suspect
pick its printed version where the arbiter is unsure, so fewer suspects go to review?

qwen3.8 (thinking on) gets the lines around the suspect's line with the place marked,
the versions, how often each appears in the book's text layer, and what OCR tends to
confuse. Its answer is held to the versions' letters (structured output) and read with
the letters' probabilities, so it picks and never rewrites.

Items come from the trust data (`work/probes/ocr-trust/`), each version labelled. Per
golden tuning book, the arbiter trained without that book decides as the pipeline does
(`trust.decide`, a question a page, asking below 0.8): the suspects it asks, the ones it
settles wrongly without asking, and a seeded sample it settles rightly (the control).
For a book labelled by a reviewer's answers (Ex-minnaar, Stella) every row was asked,
and the arbiter weighed against is trained without that book, its answers left out.
Validation and first-look books are never read.

    uv run python experiments/probe_context_judge.py items   # freeze the set, no models
    uv run python experiments/probe_context_judge.py run [--limit N] [--via openrouter:…]
    uv run python experiments/probe_context_judge.py score [--via openrouter:…]

`--via` asks a hosted build instead (`clients/openrouter.py`, only where the user allowed
it): DeepInfra's bf16 Qwen, its thinking capped near the local model's length, takes the
letters' schema but gives no log-probabilities, so its pick counts as sure. Answers are kept per model.

Items, answers and timings stay in work/probes/context-judge/ (they quote the books).
"""

import hashlib
import json
import math
import random
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import httpx
from rapidfuzz.distance import Levenshtein

from roboscriptorium import bench, ocr, trust, trustdata
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.files import append_jsonl, read_jsonl, write_atomic
from roboscriptorium.pdf import cached_text_layer

OUT = Path("work/probes/context-judge")
MODEL = "qwen3.8:27b-nvfp4"
AROUND = 8  # lines either side of the suspect's line
CONTROL = 8  # suspects a golden book's arbiter settles rightly, sampled per book
SEED = 17
LETTERS = "ABCDEFGH"
ANSWER_BOOKS = ("ex-minnaar", "stella")

PROMPT = """You are proofreading the OCR of a printed {language} book. The OCR readings \
disagree about one place, marked ⟦?⟧ in the line marked » below. Decide which version \
the printed page shows.

Text around it, as OCR read it (other small slips are possible):
{context}

Versions for ⟦?⟧:
{versions}

Weigh grammar and meaning in context, and how this book writes the word elsewhere (the \
counts are over its whole OCR text, this place included). OCR confuses look-alike \
letters (c and e, rn and m, l, I and 1), drops or adds accents, and reads small capitals \
as mixed case ("BMw" for "BMW"). In Dutch a stress accent sits on both letters of a \
doubled vowel ("vóór", "vráág"). Choose what the page prints, even where it looks \
unusual: don't correct the author or the printer. Answer with the letter."""


def body_layer(book: Book) -> dict[int, list[str]]:
    lang = ocr.language(book.language)
    layer = cached_text_layer(book.source, book.stages / "textlayer.json", lang)
    first, last = book.body_pages
    return {p.number: [ln.text for ln in p.lines] for p in layer if first <= p.number <= last}


def context(pages: dict[int, list[str]], s) -> str:
    """The lines around the suspect's, across page ends, its own marked and its place
    replaced by ⟦?⟧. The line is found on its page by its text (an added line, which
    the layer lacks, goes in at its index)."""
    flat = [(n, t) for n in sorted(pages) for t in pages[n]]
    own = [i for i, (n, _) in enumerate(flat) if n == s.page]
    marked = s.original[: s.start] + "⟦?⟧" + s.original[s.end :]
    if own:
        best = min(own, key=lambda i: Levenshtein.normalized_distance(flat[i][1], s.original))
        if Levenshtein.normalized_distance(flat[best][1], s.original) < 0.3:
            at, add = best, False
        else:
            at, add = own[0] + min(s.line, len(own)), True
    else:
        at, add = 0, True
    before = flat[max(0, at - AROUND) : at]
    after = flat[at + (0 if add else 1) : at + (0 if add else 1) + AROUND]
    return "\n".join(
        [f"  {t}" for _, t in before] + [f"» {marked}"] + [f"  {t}" for _, t in after]
    )


def counts(pages: dict[int, list[str]], versions: list[str]) -> list[int]:
    text = "\n".join(t for n in sorted(pages) for t in pages[n])
    out = []
    for v in versions:
        v = v.strip()
        if not v:
            out.append(0)
            continue
        # A whole token: "Je" isn't counted inside "‘Je".
        out.append(len(re.findall(r"(?<!\S)" + re.escape(v) + r"(?!\w)", text)))
    return out


def held_out_arbiter(name: str, settings: Settings) -> trust.Trust:
    """The arbiter the pipeline would use on a book it wasn't trained on."""
    path = trust.without(Path(settings.ocr_trust_model), name)
    if path.exists():
        return trust.load(path)
    names = [
        n
        for n in trustdata.SPECS
        if n != name and trustdata.trainable(n) and not trustdata.usable(n, settings)
    ]
    every = [r for n in names for r in trustdata.rows_of(n, settings)]
    return trust.train(
        [r["s"] for r in every],
        [r["right"] for r in every],
        [r["book"] for r in every],
        trustdata.weighed(settings),
    )


def pages_read(book: Book, spec: str) -> int:
    rng = spec.split(":")[0] if spec and spec != "answers" else ""
    first, last = map(int, rng.split("-")) if rng else book.body_pages
    return last - first + 1


def items() -> None:
    settings = Settings.from_env()
    tuning = [n for n in trustdata.SPECS if n in bench.TRAINED_ON]
    out = []
    rng = random.Random(SEED)
    for name in tuning + list(ANSWER_BOOKS):
        if why := trustdata.usable(name, settings):
            print(f"skipped {name}: {why}")
            continue
        book = Book.load(Path("work") / name)
        rows = [r for r in trustdata.rows_of(name, settings) if any(r["right"])]
        model = held_out_arbiter(name, settings)
        probs = [trust.probabilities(model, r["s"]) for r in rows]
        if name in ANSWER_BOOKS:
            strata = ["asked"] * len(rows)
        else:
            budget = round(settings.ocr_questions_per_page * pages_read(book, trustdata.SPECS[name]))
            decided = trust.decide([r["s"] for r in rows], model, budget, settings.ocr_ask_below)
            strata = []
            for r, d, p in zip(rows, decided, probs, strict=True):
                if d.choice == "review":
                    strata.append("asked")
                else:
                    strata.append("silent-right" if r["right"][int(p.argmax())] else "silent-wrong")
            right = [i for i, k in enumerate(strata) if k == "silent-right"]
            keep = set(rng.sample(right, min(CONTROL, len(right))))
            strata = [
                "control" if i in keep else (None if k == "silent-right" else k)
                for i, k in enumerate(strata)
            ]
        pages = body_layer(book)
        lang = "Dutch" if book.language.lower().startswith("nl") else "English"
        for r, p, kind in zip(rows, probs, strata, strict=True):
            if kind is None:
                continue
            s = r["s"]
            versions = [s.ours, *s.others]
            n = counts(pages, versions)
            listed = "\n".join(
                f"{LETTERS[i]}) {json.dumps(v, ensure_ascii=False)}: {c} times in the book"
                for i, (v, c) in enumerate(zip(versions, n, strict=True))
            )
            prompt = PROMPT.format(language=lang, context=context(pages, s), versions=listed)
            out.append(
                {
                    "id": f"{name}:{s.page}:{s.line}:{s.start}",
                    "book": name,
                    "kind": kind,
                    "versions": versions,
                    "right": r["right"],
                    "arbiter": [float(x) for x in p],
                    "prompt": prompt,
                }
            )
        kinds = Counter(i["kind"] for i in out if i["book"] == name)
        print(f"{name}: {dict(kinds)}")
    OUT.mkdir(parents=True, exist_ok=True)
    write_atomic(OUT / "items.json", json.dumps(out, ensure_ascii=False, indent=1))
    print(f"{len(out)} items, {dict(Counter(i['kind'] for i in out))}")


def ask(client: httpx.Client, item: dict) -> dict:
    letters = list(LETTERS[: len(item["versions"])])
    started = time.monotonic()
    resp = client.post(
        "/api/chat",
        json={
            "model": MODEL,
            "stream": False,
            "think": True,
            "logprobs": True,
            "top_logprobs": 10,
            "messages": [{"role": "user", "content": item["prompt"]}],
            "format": {
                "type": "object",
                "properties": {"answer": {"type": "string", "enum": letters}},
                "required": ["answer"],
            },
            "options": {"temperature": 0},
        },
    )
    resp.raise_for_status()
    r = resp.json()
    answer = json.loads(r["message"]["content"])["answer"]
    # The letter's position in the answer: its top alternatives give the probabilities.
    probs = {}
    for t in reversed(r.get("logprobs") or []):
        if t["token"].strip() == answer:
            for alt in t["top_logprobs"]:
                k = alt["token"].strip()
                if k in letters and k not in probs:
                    probs[k] = math.exp(alt["logprob"])
            break
    total = sum(probs.values()) or 1.0
    return {
        "id": item["id"],
        "prompt": hashlib.sha1(item["prompt"].encode()).hexdigest()[:10],
        "pick": letters.index(answer),
        "probs": [probs.get(k, 0.0) / total for k in letters],
        "thinking": r["message"].get("thinking", ""),
        "tokens": r.get("eval_count"),
        "seconds": round(time.monotonic() - started, 1),
    }


def ask_hosted(via: str, item: dict) -> dict:
    from roboscriptorium.clients import openrouter

    name, provider = openrouter.parse(via)
    letters = list(LETTERS[: len(item["versions"])])
    started = time.monotonic()
    body = {
        "model": name,
        "temperature": 0,
        "messages": [{"role": "user", "content": item["prompt"]}],
        # Uncapped, the hosted build thinks ~8,000 tokens where the local one thinks
        # 500–1,500; capped, it picked as the local one did on the first three items.
        "reasoning": {"max_tokens": 1500},
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "answer",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {"answer": {"type": "string", "enum": letters}},
                    "required": ["answer"],
                    "additionalProperties": False,
                },
            },
        },
        "provider": {**openrouter._routing(provider), "require_parameters": True},
    }
    r = openrouter._post(openrouter.URL, body, None)
    message = r["choices"][0]["message"]
    answer = json.loads(message["content"])["answer"]
    return {
        "id": item["id"],
        "prompt": hashlib.sha1(item["prompt"].encode()).hexdigest()[:10],
        "pick": letters.index(answer),
        "probs": [1.0 if k == answer else 0.0 for k in letters],
        "thinking": message.get("reasoning") or "",
        "tokens": r.get("usage", {}).get("completion_tokens"),
        "seconds": round(time.monotonic() - started, 1),
    }


def answers_path(via: str | None) -> Path:
    tag = (via or MODEL).replace(":", "_").replace("/", "_")
    return OUT / f"answers-{tag}{'-nocounts' if NO_COUNTS else ''}.jsonl"


def without_counts(prompt: str) -> str:
    """The prompt without the versions' counts in the book (`--no-counts`): with them the
    judge read "wc" as "we" (241 times in Ex-minnaar against 9) where the sentence said wc."""
    prompt = re.sub(r": \d+ times in the book", "", prompt)
    return prompt.replace(
        "Weigh grammar and meaning in context, and how this book writes the word elsewhere (the "
        "counts are over its whole OCR text, this place included). ",
        "Weigh grammar and meaning in context. ",
    )


def run(limit: int | None, via: str | None, kinds: set[str] | None = None) -> None:
    every = json.loads((OUT / "items.json").read_text())
    if NO_COUNTS:
        every = [{**i, "prompt": without_counts(i["prompt"])} for i in every]
    if kinds:
        every = [i for i in every if i["kind"] in kinds]
    path = answers_path(via)
    done = {
        (a["id"], a["prompt"]) for a in (read_jsonl(path) if path.exists() else [])
    }
    todo = [
        i
        for i in every
        if (i["id"], hashlib.sha1(i["prompt"].encode()).hexdigest()[:10]) not in done
    ]
    # Asked first: they are what the probe is for; the controls check it breaks nothing.
    order = {"asked": 0, "silent-wrong": 1, "control": 2}
    todo.sort(key=lambda i: order[i["kind"]])
    if limit:
        todo = todo[:limit]
    print(f"{len(todo)} to ask, {len(done)} cached", flush=True)
    seconds = []
    if via:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(8) as pool:
            for n, (item, a) in enumerate(
                zip(todo, pool.map(lambda i: ask_hosted(via, i), todo), strict=True), 1
            ):
                append_jsonl(path, a)
                print(
                    f"[{n}/{len(todo)}] {item['id']} {item['kind']} pick {LETTERS[a['pick']]} "
                    f"({'right' if item['right'][a['pick']] else 'WRONG'}) {a['seconds']}s",
                    flush=True,
                )
        return
    with httpx.Client(base_url=Settings.from_env().ollama_url, timeout=900) as client:
        for n, item in enumerate(todo, 1):
            a = ask(client, item)
            append_jsonl(path, a)
            seconds.append(a["seconds"])
            mean = sum(seconds) / len(seconds)
            print(
                f"[{n}/{len(todo)}] {item['id']} {item['kind']} pick {LETTERS[a['pick']]} "
                f"({'right' if item['right'][a['pick']] else 'WRONG'}) {a['seconds']}s "
                f"{a['tokens']} tok, ~{mean * (len(todo) - n) / 60:.0f} min left",
                flush=True,
            )


def score(via: str | None) -> None:
    every = {i["id"]: i for i in json.loads((OUT / "items.json").read_text())}
    if NO_COUNTS:
        every = {k: {**i, "prompt": without_counts(i["prompt"])} for k, i in every.items()}
    path = answers_path(via)
    answers = {a["id"]: a for a in read_jsonl(path) if a["id"] in every}
    by = defaultdict(list)
    for k, a in answers.items():
        i = every[k]
        group = "answers" if i["book"] in ANSWER_BOOKS else "golden"
        by[(group, i["kind"])].append((i, a))
    print(f"{len(answers)} of {len(every)} answered; median "
          f"{sorted(a['seconds'] for a in answers.values())[len(answers) // 2]} s a call")
    for (group, kind), pairs in sorted(by.items()):
        n = len(pairs)
        judge = sum(i["right"][a["pick"]] for i, a in pairs)
        arb = sum(i["right"][max(range(len(i["arbiter"])), key=i["arbiter"].__getitem__)]
                  for i, _ in pairs)
        print(f"\n{group} {kind}: {n} suspects; context judge right {judge} ({judge / n:.0%}),"
              f" arbiter's likeliest right {arb} ({arb / n:.0%})")
        for cut in (0.9, 0.99):
            sure = [(i, a) for i, a in pairs if max(a["probs"]) >= cut]
            wrong = sum(not i["right"][a["pick"]] for i, a in sure)
            print(f"  sure ≥ {cut}: {len(sure)} ({len(sure) / n:.0%}), {wrong} of them wrong")
        both = [(i, a) for i, a in pairs
                if a["pick"] == max(range(len(i["arbiter"])), key=i["arbiter"].__getitem__)]
        wrong = sum(not i["right"][a["pick"]] for i, a in both)
        print(f"  judge and arbiter agree: {len(both)}, {wrong} of them wrong")
    wrongs = [(every[k], a) for k, a in answers.items()
              if every[k]["kind"] == "asked" and not every[k]["right"][a["pick"]]
              and max(a["probs"]) >= 0.9]
    print("\nSure and wrong on asked suspects (up to 15):")
    for i, a in wrongs[:15]:
        print(f"  {i['id']}: picked {i['versions'][a['pick']]!r}, the print "
              f"{[v for v, r in zip(i['versions'], i['right'], strict=True) if r]}")


NO_COUNTS = "--no-counts" in sys.argv

if __name__ == "__main__":
    step = sys.argv[1]
    via = sys.argv[sys.argv.index("--via") + 1] if "--via" in sys.argv else None
    if step == "items":
        items()
    elif step == "run":
        limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
        kinds = set(sys.argv[sys.argv.index("--kinds") + 1].split(",")) if "--kinds" in sys.argv else None
        run(limit, via, kinds)
    elif step == "score":
        score(via)
