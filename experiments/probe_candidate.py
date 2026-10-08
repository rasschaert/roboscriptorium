"""Probe: is a scan and an EPUB a fit golden pair? No models.

Reads the scan's text layer and the EPUB's text, aligns them word by word
(`golden.align`) and reports what a manifest needs and how far the two differ:
the scan's kind (producer, text-layer font, image ppi), the EPUB's edition
(publisher, date, ISBN) and its headings and classes, the body page range, the
text layer's character error rate against the EPUB per band of pages, the chapter
headings found on the scan, and the most frequent word differences, which tell OCR
slips (a letter) from edition differences (other words, other punctuation).

    uv run python experiments/probe_candidate.py <scan.pdf> <reference.epub> [heading-prefix ...]

Headings are h1-h6, or paragraphs whose class starts with a prefix ("kop" by
default). The report also goes to work/probes/candidates/<scan stem>.txt.
"""

import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

import pymupdf
from rapidfuzz.distance import Levenshtein

from roboscriptorium import pdf
from roboscriptorium.evaluate import normalise
from roboscriptorium.golden import align, epub
from roboscriptorium.golden.reference import unmarked
from roboscriptorium.ir import SourceRef

BAND = 20  # pages per CER band
BODY_LINES = 3  # a page with this many body lines is a body page

scan, ref = Path(sys.argv[1]), Path(sys.argv[2])
prefixes = tuple(sys.argv[3:]) or ("kop",)
report: list[str] = []


def say(*parts):
    text = " ".join(str(p) for p in parts)
    print(text)
    report.append(text)


# The scan.
with pymupdf.open(scan) as doc:
    meta = doc.metadata
    count = len(doc)
    mid = doc[count // 2]
    fonts = sorted({f[3] for f in mid.get_fonts()})
    ppi = sorted({round(72 * i["width"] / (i["bbox"][2] - i["bbox"][0])) for i in mid.get_image_info()})
    sizes = Counter((round(p.rect.width), round(p.rect.height)) for p in doc)
say(f"scan {scan.name}: {count} pages, creator {meta.get('creator')!r}, producer {meta.get('producer')!r}")
say(f"  mid page: text-layer fonts {fonts}, image ppi {ppi}; commonest page size {sizes.most_common(1)[0]}")

# The EPUB.
DC, OPF, CONTAINER = (
    "{http://purl.org/dc/elements/1.1/}",
    "{http://www.idpf.org/2007/opf}",
    "{urn:oasis:names:tc:opendocument:xmlns:container}",
)
with zipfile.ZipFile(ref) as z:
    drm = any(n.endswith("META-INF/encryption.xml") for n in z.namelist())
    opf_path = ET.fromstring(z.read("META-INF/container.xml")).find(f".//{CONTAINER}rootfile")
    opf_path = opf_path.get("full-path")
    opf = ET.fromstring(z.read(opf_path))
    dc = lambda tag: [(e.text or "").strip() for e in opf.iter(f"{DC}{tag}")]  # noqa: E731
    manifest = {i.get("id"): unquote(i.get("href")) for i in opf.iter(f"{OPF}item")}
    base = Path(opf_path).parent
    files = [str(base / manifest[r.get("idref")]) for r in opf.iter(f"{OPF}itemref")]
    files = [f for f in files if f.lower().endswith((".xhtml", ".html", ".htm"))]
    classes, tags = Counter(), Counter()
    for f in files:
        raw = z.read(f).decode("utf-8", "replace")
        classes.update(re.findall(r'class="([^"]*)"', raw))
        tags.update(re.findall(r"<(h[1-6])[ >]", raw))
say(f"epub {ref.name}: publisher {dc('publisher')}, date {dc('date')[:1]}, language {dc('language')}")
say(f"  identifiers {[i for i in dc('identifier') if i]}; DRM {'yes' if drm else 'no'}")
say(f"  {len(files)} spine files; heading tags {dict(tags)}; classes {classes.most_common(12)}")

notes: list[str] = []
sections = epub.read(
    ref, files, prefixes, italic=frozenset({"italic"}), blank=frozenset({"bodybefore"}),
    notes=frozenset({"noten"}), found_notes=notes,
)
ref_words = sum(len(unmarked(p).split()) for s in sections for p in s.paragraphs)
say(f"reference: {len(sections)} headings, {sum(len(s.paragraphs) for s in sections)} paragraphs,"
    f" {ref_words} words, {len(notes)} notes (heading prefixes {prefixes})")
say("  headings:", " | ".join(s.heading[:28] for s in sections[:50]))
if not sections:
    sys.exit("no headings found: pass the heading class prefix")

# The text layer against the reference.
pages = pdf.read_text_layer(scan)
labels = align.align(pages, sections)
page_map, body_pages, heading_lines = [], [], []
dist, chars, exact, lines_scored = Counter(), Counter(), Counter(), Counter()
pairs: Counter[tuple[str, str]] = Counter()
for p in pages:
    roles = Counter()
    for k, line in enumerate(p.lines):
        truth = labels[SourceRef(p.number, k)]
        roles[truth.role] += 1
        if truth.role == "other":
            continue
        if truth.role == "heading":
            heading_lines.append((p.number, line.text))
        band = (p.number - 1) // BAND
        got, want = normalise(line.text), normalise(truth.truth)
        d = Levenshtein.distance(got, want)
        dist[band] += d
        chars[band] += len(want)
        exact[band] += d == 0
        lines_scored[band] += 1
        if d:
            a, b = got.split(), want.split()
            for op in Levenshtein.opcodes(a, b):
                if op.tag == "replace" and op.src_end - op.src_start == op.dest_end - op.dest_start:
                    for i, j in zip(range(op.src_start, op.src_end), range(op.dest_start, op.dest_end)):
                        pairs[(a[i], b[j])] += 1
    is_body = roles["body"] >= BODY_LINES
    page_map.append("h" if roles["heading"] else "B" if is_body else "." if roles["other"] else " ")
    if is_body or roles["heading"]:
        body_pages.append(p.number)
say(f"body pages {body_pages[0]}-{body_pages[-1]} of {count} (B body, h heading, . only unmatched lines):")
for start in range(0, count, 50):
    say(f"  {start + 1:4d} {''.join(page_map[start:start + 50])}")
say(f"headings on the scan: {len(heading_lines)} lines for {len(sections)} reference headings")
say("  " + " | ".join(f"p{n} {t[:28]}" for n, t in heading_lines[:50]))
say("text layer against the reference, per band of pages (CER, lines exact):")
total_d = total_c = total_e = total_n = 0
for band in sorted(chars):
    total_d += dist[band]; total_c += chars[band]; total_e += exact[band]; total_n += lines_scored[band]
    say(f"  {band * BAND + 1:4d}-{(band + 1) * BAND:<4d} CER {100 * dist[band] / max(1, chars[band]):5.2f}%"
        f"  exact {exact[band]}/{lines_scored[band]}")
say(f"  all       CER {100 * total_d / max(1, total_c):5.2f}%  exact {total_e}/{total_n}")
say("most frequent word differences (layer -> reference):")
for (a, b), n in pairs.most_common(40):
    say(f"  {n:4d}  {a!r} -> {b!r}")

out = Path("work/probes/candidates") / f"{scan.stem}.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(report) + "\n")
