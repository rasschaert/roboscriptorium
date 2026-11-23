#!/usr/bin/env zsh
# What holds the GPU right now, from the machine itself rather than the queue's view: the
# model lock's holder (the process with the lock file open that has work running under it;
# one blocked waiting has none), the processes waiting for it, and what Ollama has loaded.
#   experiments/gpu-now.sh
set -uo pipefail
cd "${0:A:h}/.."
zmodload zsh/system
for lock in work/runs/model-screen.lock work/runs/cpu-heavy.lock; do
  [[ -e $lock ]] || continue
  if ( zsystem flock -t 0 $lock ) 2>/dev/null; then print "${lock:t}: free"; continue; fi
  for p in $(lsof -t $lock 2>/dev/null | sort -u); do
    kids=$(pgrep -P $p | wc -l | tr -d ' ')
    what=$(ps -o command= -p $p | cut -c1-90)
    run=$(ps -o command= -p $(pgrep -P $p | head -1) 2>/dev/null | cut -c1-90)
    if (( kids )); then print "${lock:t}: held by $p $what -> $run"; else print "${lock:t}: waiting $p $what"; fi
  done
done
print "screens: $({ screen -ls || true; } | grep -o 'robo-[^[:space:]]*' | tr '\n' ' ')"
ollama ps | awk 'NR > 1 {print "ollama loaded: " $1}'
