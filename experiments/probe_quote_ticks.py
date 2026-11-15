"""Beside `probe_nested_quotes.py`: for each of its rows, the number of raised ink marks
at the word's edge on the scan (1 for ‘, 2 for “, 3 for ‘“), printed by book and label.
No models.

    uv run python experiments/probe_quote_ticks.py
"""

import json, sys
from collections import Counter
from pathlib import Path
import numpy as np, pymupdf
sys.path.insert(0,'experiments')
import probe_nested_quotes as pn
from roboscriptorium import pdf as pdflayer, rendercheck
from roboscriptorium.book import Book
from roboscriptorium.pdf import cached_text_layer

def ticks(page, word, opening):
    ink = pn.strip(page, word)
    if ink is None: return None
    high = word[3]-word[1]; scale = rendercheck.DPI/72
    mask = ink > 0.5
    cols = mask.any(0)
    inked = np.where(cols)[0]
    if not len(inked): return None
    lows = np.array([np.where(mask[:,c])[0][-1] for c in inked]); tops = np.array([np.where(mask[:,c])[0][0] for c in inked])
    base, top = np.median(lows), np.quantile(tops, 0.1)
    middle = top + 0.5*(base-top)
    idx = range(len(cols)) if opening else range(len(cols)-1,-1,-1)
    runs=[]; cur=None
    for c in idx:
        if cols[c]:
            cur = [c,c] if cur is None else [cur[0],c]
        elif cur is not None:
            runs.append(cur); cur=None
    if cur is not None: runs.append(cur)
    n=0
    for c0,c1 in runs:
        lo,hi=min(c0,c1),max(c0,c1)+1
        rows=np.where(mask[:,lo:hi].any(1))[0]
        if len(rows) and rows[-1] < middle and hi-lo <= high*scale*0.5: n+=1
        else: break
    return n
rows=[json.loads(l) for l in open('work/probes/nested-quotes.jsonl')]
books={}; c=Counter()
out=[]
for r in rows:
    if r['book'] not in books:
        book=Book.load(Path('work')/r['book']); books[r['book']]=(pymupdf.open(book.source),{p.number:p for p in cached_text_layer(book.source, book.stages/'textlayer.json')})
    doc,pages=books[r['book']]
    w=next(w for w in pdflayer.page_words(doc[r['page']-1], pages[r['page']]) if w[4]==r['word'])
    n=ticks(doc[r['page']-1], w, r['marked'].endswith(r['word']))
    c[(r['book'][:8], 'lost' if r['lost'] else 'plain', n)]+=1
    out.append({**r,'ticks':n})
for k in sorted(c, key=str): print(k,c[k])
json.dump(out,open('work/probes/nested-quotes-ticks.json','w'),ensure_ascii=False)
