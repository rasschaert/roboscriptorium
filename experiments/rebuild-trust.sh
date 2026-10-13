#!/usr/bin/env zsh
# Rebuilds every book's trust data from cold, one book at a time, then retrains the
# arbiter and runs the tuning bench. Each step is timed (timed.sh, which also waits for
# the battery) and logged in work/runs/rebuild/<step>.log; a line per finished step goes
# to work/runs/rebuild/progress.txt. A step that fails is recorded and the chain goes on
# to the next book; training and the bench run only when every book succeeded. To pause
# after the book under way, create work/runs/rebuild/STOP; delete it before restarting.
# Books whose trust data exists are skipped, so a restart goes on where it stopped.
#   experiments/detached.sh rebuild experiments/rebuild-trust.sh
set -uo pipefail
mkdir -p work/runs/rebuild
progress=work/runs/rebuild/progress.txt
books=(${(f)"$(uv run python -c '
import sys; sys.path.insert(0, "experiments")
from roboscriptorium.trustdata import SPECS
from roboscriptorium.book import Book
from pathlib import Path
for b, spec in SPECS.items():
    if b == "stella":
        continue
    first, last = map(int, spec.split(":")[0].split("-")) if spec else Book.load(Path("work") / b).body_pages
    print(b, last - first + 1)
')"})
failed=0
for row in $books; do
  book=${row% *} pages=${row#* }
  if [[ -e work/runs/rebuild/STOP ]]; then
    print "$(date '+%F %H:%M') paused before $book (STOP file)" >> $progress
    exit 0
  fi
  [[ -s work/probes/ocr-trust/$book.json ]] && continue
  experiments/timed.sh "trust data, $book, cold after work/ was lost, Qwen local" $pages \
    work/runs/rebuild/$book.log uv run python experiments/ocr_trust_data.py --rebuild $book
  code=$?
  print "$(date '+%F %H:%M') $book $pages pages exit $code" >> $progress
  (( code )) && failed=1
done
if (( failed )); then
  print "$(date '+%F %H:%M') stopped: a book failed, no training" >> $progress
  exit 1
fi
# --partial: Stella's data comes from its review answers, which this loop doesn't build.
experiments/timed.sh "train arbiter after the rebuild" 0 work/runs/rebuild/train.log \
  env PYTHONPATH=experiments uv run python experiments/train_ocr_trust.py --save --partial
code=$?
print "$(date '+%F %H:%M') train exit $code" >> $progress
(( code )) && exit 1
# The bench's own slices, which differ from the trust data's for some books.
bench_pages=$(uv run python -c '
from pathlib import Path
from roboscriptorium import bench
from roboscriptorium.book import Book
total = 0
for spec in bench.SETS["tuning"]:
    name, *rest = spec.split(":")
    first, last = map(int, rest[0].split("-")) if rest else Book.load(Path("work") / name).body_pages
    total += last - first + 1
print(total)
')
experiments/timed.sh "bench tuning, new baseline after the rebuild" $bench_pages \
  work/runs/rebuild/bench-tuning.log uv run roboscriptorium bench tuning
code=$?
print "$(date '+%F %H:%M') bench tuning exit $code" >> $progress
