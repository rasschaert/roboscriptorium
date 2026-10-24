"""Does Qwen tell `init`'s page kinds apart better than clef-flash? (the checklist, "Page kinds
for `init` by Qwen"). The same question `pagekinds.kinds` asks on the 8 pages at either edge,
put to a generative model as lettered options with the page image, one token generated: each
option's probability is its letter's in the first token's top log-probabilities. Scored as
`probe_init_ends.py` scores clef-flash: the text proper's two ends against
`tryouts/page-kinds-v1.json`.

    uv run python experiments/probe_page_kinds_qwen.py [model]

Answers are cached per book in work/probes/page-kinds/edges-chat_<model>-<book>.json.
"""

import base64
import json
import math
import string
import sys
from pathlib import Path

import httpx

from roboscriptorium import pagekinds
from roboscriptorium.clients.decide import Answer
from roboscriptorium.config import Settings
from roboscriptorium.pagekinds import ends
from roboscriptorium.pdf import cached_text_layer

OUT = Path("work/probes/page-kinds")


class ChatChoice:
    """`decide`'s interface over a generative model: a choice's options as letters, the
    letter tokens' probabilities as the answer's."""

    def __init__(self, model: str, url: str):
        self.model = f"chat:{model}"
        self.name, self.url = model, url

    def decide(self, state: dict, questions: dict, image_png: bytes | None = None) -> dict:
        out = {}
        for key, q in questions.items():
            options = list(q["criteria"].items())
            letters = string.ascii_uppercase[: len(options)]
            prompt = (
                f"{q['instructions']}\n\nWhat the text layer reads on the page:\n"
                f"{json.dumps(state, ensure_ascii=False)}\n\n"
                + "\n".join(f"{c}. {text}" for c, (_, text) in zip(letters, options, strict=True))
                + "\n\nAnswer with the letter only."
            )
            body = {
                "model": self.name, "stream": False, "think": False,
                "messages": [{"role": "user", "content": prompt,
                              "images": [base64.b64encode(image_png).decode()] if image_png else []}],
                "logprobs": True, "top_logprobs": 20, "options": {"num_predict": 1, "temperature": 0},
            }  # fmt: skip
            resp = httpx.post(f"{self.url}/api/chat", json=body, timeout=900)
            resp.raise_for_status()
            top = (resp.json().get("logprobs") or [{}])[0].get("top_logprobs", [])
            p = {c: sum(math.exp(a["logprob"]) for a in top if a["token"].strip() == c) for c in letters}
            total = sum(p.values()) or 1.0
            probs = {name: p[c] / total for c, (name, _) in zip(letters, options, strict=True)}
            best = max(probs, key=probs.get)
            out[key] = Answer("choice", best, probs[best], probs)
        return out


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else Settings.from_env().read_model
    client = ChatChoice(model, Settings.from_env().ollama_url)
    labels = json.loads(Path("tryouts/page-kinds-v1.json").read_text())["books"]
    right = {"first": 0, "last": 0, "books": 0}
    for name, entry in sorted(labels.items()):
        book = Path("work") / name
        if not (book / "source.pdf").exists():
            continue
        pages = cached_text_layer(book / "source.pdf", book / "stages" / "textlayer.json")
        cache = OUT / f"edges-chat_{model.replace(':', '_')}-{name}.json"
        kinds = pagekinds.kinds(book / "source.pdf", pages, client, cache)
        want = {int(k): v for k, v in entry["pages"].items()}
        want = {p.number: want.get(p.number, "text") for p in pages}
        w, g = ends(want), ends(kinds)
        right["first"] += w[0] == g[0]
        right["last"] += w[1] == g[1]
        right["books"] += 1
        off = pagekinds.printed_offset(pages)
        mark = "" if w == g else f"  <- labelled {pagekinds.page_label(w[0], off)} to {pagekinds.page_label(w[1], off)}"
        print(f"{name[:34]:34} got {pagekinds.page_label(g[0], off)} to {pagekinds.page_label(g[1], off)}{mark}", flush=True)
    print("ends right:", right)
