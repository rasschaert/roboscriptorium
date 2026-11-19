"""Which lines `chapters.numbers_over_titles` makes chapter numbers, and `title_lines`
runs on into a title ("title-runs-on"), on every bench book,
from warm caches (a model question fails: run with ROBO_OLLAMA_URL at a dead port), to
read each against the scan before it builds. No models.

    ROBO_OLLAMA_URL=http://127.0.0.1:9 uv run python experiments/probe_numbers_over_titles.py
"""

from roboscriptorium import bench, chapters
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring


class Stop(Exception):
    pass


def main() -> None:
    seen: list = []
    rule, titles = chapters.numbers_over_titles, chapters.title_lines

    def watched(pages, roles):
        out = rule(pages, roles)
        lines = {(p.number, i): ln.text for p in pages for i, ln in enumerate(p.lines)}
        for ref in out:
            if out[ref] != roles.get(ref):
                below = lines.get((ref.page, ref.line + 1), "")
                seen.append((ref.page, "number", lines[(ref.page, ref.line)], below))
        raise Stop

    def runs_on(pages, roles, styles):
        out = titles(pages, roles, styles)
        lines = {(p.number, i): ln.text for p in pages for i, ln in enumerate(p.lines)}
        for ref, role in out.items():
            if role.rule == "title-runs-on":
                above = lines.get((ref.page, ref.line - 1), "")
                seen.append((ref.page, "runs on", lines[(ref.page, ref.line)], above))
        return out

    chapters.numbers_over_titles = watched
    chapters.title_lines = runs_on
    for spec in bench.SETS["tuning"] + bench.SETS["validation"]:
        name = spec.split(":")[0]
        seen.clear()
        try:
            scoring.build(f"work/{spec}", bench.unseen(Settings.from_env(), name))
        except Stop:
            pass
        except Exception as e:  # noqa: BLE001
            print(f"{name}: not warm ({type(e).__name__})")
            continue
        print(f"{name}: {len(seen)}", *(f"\n  PDF {p} {k}: {t!r} / {b!r}" for p, k, t, b in seen))


if __name__ == "__main__":
    main()
