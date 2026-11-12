"""Match books' typefaces ahead of a run with the judge `render` (`rendercheck.match`,
kept in each book's stages/typeface.json), so a rebuild or a bench doesn't wait on them.

    uv run python experiments/match_typefaces.py --list      # every book a bench or the trust data reads
    uv run python experiments/match_typefaces.py <book> …    # e.g. through xargs -P
"""

import sys
from pathlib import Path

from roboscriptorium import bench, rendercheck
from roboscriptorium.book import Book
from roboscriptorium.config import Settings
from roboscriptorium.trustdata import SPECS

if __name__ == "__main__":
    if "--list" in sys.argv:
        names = [*SPECS, *(s.split(":")[0] for k in ("tuning", "validation") for s in bench.SETS[k])]
        print("\n".join(dict.fromkeys(names)))
        sys.exit()
    for name in sys.argv[1:]:
        book = Book.load(Path("work") / name)
        found = rendercheck.match(book.source, *book.body_pages, Path(Settings.from_env().fonts),
                                  book.stages / "typeface.json")
        print(f"{name}: {found.name} {found.fit:.3f}, ink {found.spread:+d}, {found.size:.0f} px", flush=True)
