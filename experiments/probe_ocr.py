"""OCR probe on Het ivoren aapje (Teirlinck, 1909): Gutenberg #28068 with its page images.

Under copyright in the EU until 2038, so everything stays in work/het-ivoren-aapje/.

  uv run python experiments/probe_ocr.py prepare ~/Downloads/pg28068-images.epub
  uv run python experiments/probe_ocr.py run <model> [prompt]   # model: tesseract or an Ollama model

The reference per page is Gutenberg's text with the transcribers' corrections
reverted to what the print says ("Bron: ..."). Reports CER per page and lists
modernised spellings (vleesch → vlees, zijne → zijn, dàt → dat) separately from
plain misreadings: a faithful OCR must never modernise.
"""

import json
import re
import subprocess
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

import httpx
from rapidfuzz.distance import Levenshtein

ROOT = Path("work/het-ivoren-aapje")
IMAGES = "https://www.gutenberg.org/files/28068/28068-page-images/p{:04d}.png"
SAMPLE = [5, 30, 61, 100, 150, 200, 250, 300, 350, 400, 450, 500]
XHTML = "{http://www.w3.org/1999/xhtml}"

PROMPTS = {
    # TranslateGemma's documented prompt, Dutch to Dutch, with the page as the text.
    "translate": (
        "You are a professional Dutch (nl) to Dutch (nl) translator. Your goal is to accurately "
        "convey the meaning and nuances of the original Dutch text while adhering to Dutch "
        "grammar, vocabulary, and cultural sensitivities.\n"
        "Produce only the Dutch translation, without any additional explanations or commentary. "
        "Please translate the following Dutch text into Dutch:\n\n\n"
    ),
    "transcribe": (
        "Transcribe the text on this scanned book page exactly as printed: keep the original "
        "spelling, punctuation, accents and line breaks, and do not modernise or correct "
        "anything. Output only the text."
    ),
    "oldspelling": (
        "This is a page from a Dutch novel printed in 1909, in the spelling of that time "
        "(before the 1934 and 1947 reforms): for example 'zijne', 'vleesch', 'oogenblik', "
        "'tusschen', 'groote', 'teeken', 'kommissie', and accents such as 'dàt', 'éen', 'vóor'. "
        "Transcribe the page character for character exactly as printed. Never modernise or "
        "correct spelling, accents or punctuation; when a word looks old-fashioned or wrong, "
        "copy it as printed. Keep the line breaks. Output only the text."
    ),
}


# --- prepare ---------------------------------------------------------------------------


def page_texts(epub: Path) -> dict[int, str]:
    pages: dict[int, list[str]] = {}
    current = [0]

    def emit(text: str) -> None:
        pages.setdefault(current[0], []).append(text)

    def walk(el: ET.Element) -> None:
        cls = el.get("class") or ""
        if "x-ebookmaker-pageno" in cls:
            if m := re.fullmatch(r"\[(\d+)\]", el.get("title") or ""):
                current[0] = int(m.group(1))
            if el.tail:
                emit(el.tail)
            return
        if "corr" in cls.split() and (el.get("title") or "").startswith("Bron: "):
            emit(el.get("title")[len("Bron: ") :])
            if el.tail:
                emit(el.tail)
            return
        block = el.tag in {f"{XHTML}{t}" for t in ("p", "h1", "h2", "h3", "div")}
        if block:
            emit("\n\n")
        if el.text:
            emit(el.text)
        for child in el:
            walk(child)
        if block:
            emit("\n\n")
        if el.tail:
            emit(el.tail)

    with zipfile.ZipFile(epub) as z:
        names = sorted(
            (n for n in z.namelist() if re.search(r"-h-\d+\.htm\.html$", n)),
            key=lambda n: int(re.search(r"-h-(\d+)\.htm", n).group(1)),
        )
        for name in names:
            walk(ET.fromstring(z.read(name)).find(f"{XHTML}body"))
    out = {}
    for n, parts in pages.items():
        paras = [re.sub(r"\s+", " ", p).strip() for p in "".join(parts).split("\n\n")]
        out[n] = "\n\n".join(p for p in paras if p)
    return out


def prepare(epub: Path) -> None:
    (ROOT / "pages").mkdir(parents=True, exist_ok=True)
    (ROOT / "images").mkdir(parents=True, exist_ok=True)
    texts = page_texts(epub)
    for n, text in texts.items():
        if n:
            (ROOT / "pages" / f"{n:04d}.txt").write_text(text + "\n")
    for n in SAMPLE:
        img = ROOT / "images" / f"p{n:04d}.png"
        if not img.exists():
            img.write_bytes(httpx.get(IMAGES.format(n), follow_redirects=True, timeout=60).content)
    print(f"{len(texts) - 1} reference pages, {len(SAMPLE)} sample images in {ROOT}")


# --- run -------------------------------------------------------------------------------

_FOLD = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "—", "―": "—"})


def normalise_ocr(text: str) -> str:
    """One line of running text: no page number, line-end hyphens joined."""
    lines = [ln.strip() for ln in text.strip().splitlines()]
    if lines and re.fullmatch(r"[\dIlOo]{1,4}\.?", lines[0].replace(" ", "")):
        lines = lines[1:]
    joined = "\n".join(lines)
    joined = re.sub(r"(\w)-\n(\w)", r"\1\2", joined)
    return normalise(joined)


def normalise(text: str) -> str:
    """Gutenberg normalised the print's spacing ("sprak :", "mij — God"), so ignore it."""
    text = unicodedata.normalize("NFC", text).translate(_FOLD)
    text = re.sub(r"\s+([?!:;])", r"\1", text)
    text = re.sub(r"\s*—\s*", "—", text)
    # The print spaces its ellipses (". . . ."); Gutenberg closes them up.
    text = re.sub(r"\.(?:\s?\.)+", lambda m: "." * m.group().count("."), text)
    return re.sub(r"\s+", " ", text).strip()


# Spelling reforms (1934/1947 and later) between the print and modern Dutch, each a
# rewrite applied everywhere in a word. A difference is a modernisation when some
# combination of them turns the printed word into the OCR's word.
REFORMS = [
    (r"sch\b", "s"),
    (r"ssch", "ss"),
    (r"sch(?=[aeiou])", "s"),
    (r"oo", "o"),
    (r"ee", "e"),
    (r"ae", "aa"),
    (r"k(?=[aou])", "c"),
    (r"\b(zijn|mijn|hun|uw|een|har|hoog|groot|ander)e\b", r"\1"),
]


def _variants(word: str) -> set[str]:
    out = {word}
    for pattern, repl in REFORMS:
        out |= {re.sub(pattern, repl, w) for w in out}
    return out


def _accents(w: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", w) if not unicodedata.combining(c))


def modernised(old: str, new: str) -> bool:
    """Whether `new` is a modern spelling of the old word `old`, not a misreading."""
    o, n = old.strip(".,;:!?'\"—()").lower(), new.strip(".,;:!?'\"—()").lower()
    if o == n or not o or not n:
        return False
    if _accents(o) == _accents(n):
        return True  # accents dropped, added or changed (dàt → dat, éen → één)
    return _accents(n) in {_accents(v) for v in _variants(o)}


def ocr(model: str, image: Path, prompt: str) -> str:
    if model == "tesseract":
        return subprocess.run(
            ["tesseract", str(image), "-", "-l", "nld", "--tessdata-dir", "work/tessdata"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    import base64

    payload = {
        "model": model,
        "prompt": PROMPTS[prompt],
        "images": [base64.b64encode(image.read_bytes()).decode()],
        "stream": False,
        "options": {"temperature": 0, "num_ctx": 8192},
    }
    if model in THINKS_BY_DEFAULT:
        payload["think"] = False
    resp = httpx.post("http://127.0.0.1:11434/api/generate", json=payload, timeout=600)
    if resp.is_error:
        raise RuntimeError(f"{model}: HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json()["response"]


THINKS_BY_DEFAULT = {"nemotron3:33b"}


def run(model: str, prompt: str, pages: list[int]) -> None:
    out_dir = ROOT / "ocr" / f"{model.replace('/', '_').replace(':', '_')}--{prompt}"
    out_dir.mkdir(parents=True, exist_ok=True)
    mods, misreads = Counter(), Counter()
    total_edits = total_chars = 0
    for n in pages:
        ref = normalise((ROOT / "pages" / f"{n:04d}.txt").read_text())
        cached = out_dir / f"{n:04d}.txt"
        t0 = time.time()
        if not cached.exists():
            try:
                text = ocr(model, ROOT / "images" / f"p{n:04d}.png", prompt)
            except RuntimeError as exc:
                # A model stuck in a loop gets no output for that page.
                print(f"  p{n}: {exc}", flush=True)
                text = ""
            cached.write_text(text)
        dt = time.time() - t0
        got = normalise_ocr(cached.read_text())
        edits = Levenshtein.distance(got, ref)
        total_edits += edits
        total_chars += len(ref)
        rw, gw = ref.split(), got.split()
        for op in Levenshtein.opcodes(gw, rw):
            if op.tag == "replace" and op.src_end - op.src_start == op.dest_end - op.dest_start:
                for g, r in zip(gw[op.src_start : op.src_end], rw[op.dest_start : op.dest_end]):
                    (mods if modernised(r, g) else misreads)[(r, g)] += 1
            elif op.tag != "equal":
                old = " ".join(rw[op.dest_start : op.dest_end])
                misreads[(old[:40], " ".join(gw[op.src_start : op.src_end])[:40])] += 1
        print(f"  p{n}: CER {edits / max(1, len(ref)):.2%}  ({dt:.1f}s)", flush=True)
    print(f"{model} [{prompt}]: CER {total_edits / total_chars:.2%} over {len(pages)} pages")
    print(f"  modernised: {sum(mods.values())}  " + ", ".join(
        f"{r}→{g}" + (f" ×{k}" if k > 1 else "") for (r, g), k in mods.most_common(15)))
    print("  other differences (print → OCR):")
    for (r, g), k in misreads.most_common(15):
        print(f"    {k:3}× {r!r} → {g!r}")
    summary = {"model": model, "prompt": prompt, "pages": pages,
               "cer": total_edits / total_chars, "modernised": sum(mods.values())}
    with (ROOT / "ocr" / "results.jsonl").open("a") as f:
        f.write(json.dumps(summary) + "\n")


def _dir(model: str, prompt: str) -> Path:
    return ROOT / "ocr" / f"{model.replace('/', '_').replace(':', '_')}--{prompt}"


def merge(primary: list[str], plain: list[str]) -> tuple[list[str], list[tuple[int, int]]]:
    """Merge a language-model reading with a plain OCR reading of the same page.

    Where they differ only by a spelling reform, the plain OCR's older form wins (it has no
    language model to modernise with). Everything else keeps the primary reading and is
    flagged; flags are (start, end) word ranges in the merged output.
    """
    out, flags = [], []
    for op in Levenshtein.opcodes(primary, plain):
        a, b = primary[op.src_start : op.src_end], plain[op.dest_start : op.dest_end]
        if op.tag == "equal":
            out += a
        elif op.tag == "replace" and len(a) == len(b):
            for x, y in zip(a, b):
                if modernised(y, x) and _accents(x) != _accents(y):
                    out.append(y)  # a spelling reform: the plain OCR keeps the print
                else:
                    flags.append((len(out), len(out) + 1))
                    out.append(x)
        else:
            flags.append((len(out), len(out) + max(1, len(a))))
            out += a
    return out, flags


def run_merge(primary: str, plain: str, pages: list[int]) -> None:
    edits = chars = n_flags = silent = flagged_wrong = 0
    for n in pages:
        ref = normalise((ROOT / "pages" / f"{n:04d}.txt").read_text())
        a = normalise_ocr((_dir(*primary.split("@")) / f"{n:04d}.txt").read_text()).split()
        b = normalise_ocr((_dir(*plain.split("@")) / f"{n:04d}.txt").read_text()).split()
        merged, flags = merge(a, b)
        got = " ".join(merged)
        edits += Levenshtein.distance(got, ref)
        chars += len(ref)
        n_flags += len(flags)
        # Which merged words are wrong, and were they flagged?
        rw = ref.split()
        wrong = set()
        for op in Levenshtein.opcodes(merged, rw):
            if op.tag != "equal":
                wrong |= set(range(op.src_start, max(op.src_end, op.src_start + 1)))
        flagged = {i for s, e in flags for i in range(s, e)}
        silent += len(wrong - flagged)
        flagged_wrong += len(flags) - sum(1 for s, e in flags if not (set(range(s, e)) & wrong))
    print(f"merge {primary} + {plain}: CER {edits / chars:.2%}, {n_flags} flags "
          f"({flagged_wrong} of them really wrong), {silent} wrong words unflagged")


if __name__ == "__main__":
    if sys.argv[1] == "merge":
        run_merge(sys.argv[2], sys.argv[3], SAMPLE)
        sys.exit()
    if sys.argv[1] == "prepare":
        prepare(Path(sys.argv[2]).expanduser())
    else:
        model = sys.argv[2]
        prompt = sys.argv[3] if len(sys.argv) > 3 else "transcribe"
        pages = [int(p) for p in sys.argv[4].split(",")] if len(sys.argv) > 4 else SAMPLE
        run(model, prompt, pages)
