"""Which paragraphs a word's full stop and an ellipsis set as four spaced dots
(`typography._spaced_stops`) change, on every bench book, built as the bench builds it,
from warm caches (a model question fails: run with ROBO_OLLAMA_URL at a dead port). No
models.

    ROBO_OLLAMA_URL=http://127.0.0.1:9 uv run python experiments/probe_stop_ellipsis.py
"""

from roboscriptorium import bench, typography
from roboscriptorium.config import Settings
from roboscriptorium.golden import scoring


def main() -> None:
    seen: list = []
    full = typography.ellipsised

    def watched(text, style):
        new = full(text, style)
        old = typography._runs(text, style)
        if new[0] != old[0]:
            at = typography._STOP_RUN.search(text)
            k = at.start() if at else 0
            seen.append((text[max(0, k - 30) : k + 12], old[0] != text))
        return new

    typography.ellipsised = watched
    for spec in bench.SETS["tuning"] + bench.SETS["validation"]:
        name = spec.split(":")[0]
        seen.clear()
        try:
            scoring.build(f"work/{spec}", bench.unseen(Settings.from_env(), name))
        except Exception as e:  # noqa: BLE001
            print(f"{name}: not warm ({type(e).__name__})")
            continue
        print(f"{name}: {len(seen)}", *(f"\n  …{t!r}" for t, _ in seen))


if __name__ == "__main__":
    main()
