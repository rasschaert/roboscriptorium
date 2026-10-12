#!/usr/bin/env zsh
# Stops a run started by detached.sh and every process under it. Quitting the screen
# session alone leaves its command running, still sending model requests.
#   experiments/stop-run.sh <name>
set -euo pipefail
name=$1
session=$({ screen -ls || true; } | grep -o "[0-9]*\.robo-${name}[[:space:]]" || true)
if [[ -z $session ]]; then
  print -u2 "robo-$name isn't running"
  exit 1
fi
pid=${session%%.*}

descendants() {
  local child
  for child in $(pgrep -P $1 || true); do
    descendants $child
    print $child
  done
}

pids=($(descendants $pid))
(( ${#pids} )) && kill $pids 2>/dev/null || true
screen -S "robo-$name" -X quit >/dev/null 2>&1 || true
sleep 2
left=($(for p in $pids; do kill -0 $p 2>/dev/null && print $p; done; true))
if (( ${#left} )); then
  print -u2 "still running after TERM, killing: $left"
  kill -9 $left 2>/dev/null || true
fi
print "robo-$name stopped (${#pids} processes)"
