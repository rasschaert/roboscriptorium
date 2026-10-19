#!/usr/bin/env zsh
# Walks the books of a candidate list, most places first: each book's review on
# http://127.0.0.1:8765/ asks only the listed places. Ctrl-C ends a book and starts the next;
# Ctrl-C twice within two seconds stops the walk. Verdicts are saved as you answer, and a
# book you ended is skipped next time (its name goes in `<list>.done`).
#   experiments/review_batch.sh [list.json]
set -uo pipefail
cd "${0:A:h}/.."
list=${1:-work/probes/unasked/candidates-20261019.json}
cmds=("${(@f)$(uv run python experiments/review_batch_commands.py "$list" | grep -v '^#')}")
total=${#cmds}
done_file="${list}.done"
touch "$done_file"
trap ':' INT
n=0
for cmd in $cmds; do
  n=$((n + 1))
  book=${${cmd#*review work/}%% *}
  grep -qxF "$book" "$done_file" && continue
  print "\n== book $n of $total: Ctrl-C when done, the next starts (twice quickly to stop) ==\n"
  start=$SECONDS
  eval "$cmd"
  (( SECONDS - start < 2 )) && { print "stopped"; break; }
  print -r -- "$book" >> "$done_file"
done
print "done"
