"""Which lines the trees' repeat rule makes running heads with one other page (a line
holding its page's printed number, `page.carries_folio`) that it left alone with three,
on every bench book, built as the bench builds it (trees trained without the book), from
warm caches (a model question fails: run with ROBO_OLLAMA_URL at a dead port). No models.

    ROBO_OLLAMA_URL=http://127.0.0.1:9 uv run python experiments/probe_folio_heads_warm.py
"""

from roboscriptorium import bench, chapters, sorter
from roboscriptorium import page as P
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring


class Stop(Exception):
    pass


def main() -> None:
    seen: list = []
    apply, carries = sorter.apply, P.carries_folio

    def watched(*args, **kwargs):
        P.carries_folio = carries
        new = apply(*args, **kwargs)
        P.carries_folio = lambda *a: False
        try:
            old = apply(*args, **kwargs)
        finally:
            P.carries_folio = carries
        pages = args[1]
        lines = {(p.number, i): ln.text for p in pages for i, ln in enumerate(p.lines)}
        for ref in sorted(set(new) | set(old), key=lambda r: (r.page, r.line)):
            a, b = old.get(ref), new.get(ref)
            if (a and a.role) != (b and b.role):
                seen.append((ref.page, lines[(ref.page, ref.line)], a and a.role, b and b.role))
        return new

    def stop(*args, **kwargs):
        raise Stop

    sorter.apply = watched
    chapters.off_run = stop
    for spec in bench.SETS["tuning"] + bench.SETS["validation"]:
        name = spec.split(":")[0]
        seen.clear()
        try:
            scoring.build(f"work/{spec}", bench.unseen(Settings.from_env(), name))
        except Stop:
            pass
        except Exception as e:  # noqa: BLE001
            print(f"{name}: not warm ({type(e).__name__}: {e})"[:200])
            continue
        print(f"{name}: {len(seen)}", *(f"\n  PDF {p} {t!r}: {a} → {b}" for p, t, a, b in seen))


if __name__ == "__main__":
    main()
