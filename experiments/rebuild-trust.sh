#!/usr/bin/env zsh
# Rebuilds every book's trust data from cold, one book at a time, then retrains the
# arbiter and runs the tuning bench. Each step is timed (timed.sh, which also waits for
# the battery) and logged in work/runs/rebuild/<step>.log; a line per finished step goes
# to work/runs/rebuild/progress.txt. A step that fails is recorded and the chain goes on
# to the next book; training and the bench run only when every book succeeded.
#   experiments/detached.sh rebuild experiments/rebuild-trust.sh
set -uo pipefail
mkdir -p work/runs/rebuild
progress=work/runs/rebuild/progress.txt
books=(${(f)"$(uv run python -c '
import sys; sys.path.insert(0, "experiments")
from ocr_trust_data import SPECS
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
experiments/timed.sh "train arbiter after the rebuild" 0 work/runs/rebuild/train.log \
  env PYTHONPATH=experiments uv run python experiments/train_ocr_trust.py --save
print "$(date '+%F %H:%M') train exit $?" >> $progress
experiments/timed.sh "bench tuning, new baseline after the rebuild" 1792 \
  work/runs/rebuild/bench-tuning.log uv run roboscriptorium bench tuning
print "$(date '+%F %H:%M') bench tuning exit $?" >> $progress
