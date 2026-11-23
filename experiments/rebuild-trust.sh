#!/usr/bin/env zsh
# Rebuilds every book's trust data from cold, one book at a time, then retrains the
# arbiter and runs the tuning bench. Each step is timed (timed.sh, which also waits for
# the battery) and logged in work/runs/rebuild/<step>.log; a line per finished step goes
# to work/runs/rebuild/progress.txt. A step that fails is recorded and the chain goes on
# to the next book; training and the bench run only when every book succeeded. To pause
# after the book under way, create work/runs/rebuild/STOP; delete it before restarting.
# Books whose trust data exists are skipped, so a restart goes on where it stopped.
# ROBO_TRUST_DATA keeps another reader set's data apart (logs then in <it>/runs), and
# BENCH_AGAINST names the bench run to compare with; NO_BENCH=1 ends after the training.
# SIDE_BY_SIDE=<n> builds n books at once: for a rebuild whose model answers are all
# cached, the work is CPU-bound (offers redrawn, scan measures) and one book uses one core.
# Leave it at 1 when models will be asked: books side by side would swap them.
#   experiments/detached.sh rebuild experiments/rebuild-trust.sh
set -uo pipefail
data=${ROBO_TRUST_DATA:-work/probes/ocr-trust}
runs=work/runs/rebuild
[[ -n ${ROBO_TRUST_DATA:-} ]] && runs=$data/runs
mkdir -p $runs
progress=$runs/progress.txt
books=(${(f)"$(uv run python -c '
import sys; sys.path.insert(0, "experiments")
from roboscriptorium.trustdata import SPECS
from roboscriptorium.book import Book
from pathlib import Path
for b, spec in SPECS.items():
    ranged = spec and spec != "answers"
    first, last = map(int, spec.split(":")[0].split("-")) if ranged else Book.load(Path("work") / b).body_pages
    print(b, last - first + 1)
')"})
side=${SIDE_BY_SIDE:-1}
one() {  # one <book> <pages>: its trust data, a line in the progress file, a failure mark
  experiments/timed.sh "trust data, $1${ROBO_PAGE_READERS:+, page readers}" $2 \
    $runs/$1.log uv run python experiments/ocr_trust_data.py --rebuild $1
  local code=$?
  print "$(date '+%F %H:%M') $1 $2 pages exit $code" >> $progress
  (( code )) && touch $runs/$1.failed
  return 0
}
rm -f $runs/*.failed(N)
running=()
for row in $books; do
  book=${row% *} pages=${row#* }
  if [[ -e $runs/STOP ]]; then
    wait
    print "$(date '+%F %H:%M') paused before $book (STOP file)" >> $progress
    exit 0
  fi
  [[ -s $data/$book.json ]] && continue
  one $book $pages &
  running+=($!)
  while (( ${#running} >= side )); do
    alive=()
    for j in $running; do kill -0 $j 2>/dev/null && alive+=($j); done
    running=($alive)
    (( ${#running} >= side )) && sleep 5
  done
done
wait
marks=($runs/*.failed(N))
failed=$(( ${#marks} > 0 ))
if (( failed )); then
  print "$(date '+%F %H:%M') stopped: a book failed, no training" >> $progress
  exit 1
fi
experiments/timed.sh "train arbiter after the rebuild" 0 $runs/train.log \
  env PYTHONPATH=experiments uv run python experiments/train_ocr_trust.py --save
code=$?
print "$(date '+%F %H:%M') train exit $code" >> $progress
(( code )) && exit 1
[[ -n ${NO_BENCH:-} ]] && exit 0
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
against=()
[[ -n ${BENCH_AGAINST:-} ]] && against=(--against $BENCH_AGAINST)
experiments/timed.sh "bench tuning after the rebuild${ROBO_PAGE_READERS:+, page readers}" $bench_pages \
  $runs/bench-tuning.log uv run roboscriptorium bench tuning "${against[@]}"
code=$?
print "$(date '+%F %H:%M') bench tuning exit $code" >> $progress
