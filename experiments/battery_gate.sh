#!/usr/bin/env zsh
# Waits while the user's build runs, then while the battery is below 30%, checking every
# hour: Ollama drains it even on the charger. Every model run starts through it
# (`timed.sh` calls it first).
set -uo pipefail
# The user's build comes first (`priority.first` names it here): wait while it runs.
marker=work/runs/user-active
while [[ -f $marker ]] && kill -0 "$(cat $marker 2>/dev/null)" 2>/dev/null; do
  print -u2 "$(date '+%H:%M') the user's build runs: waiting"
  sleep 60
done
floor=${ROBO_BATTERY_FLOOR:-30}
while true; do
  level=$(pmset -g batt | grep -oE '[0-9]+%' | head -1 | tr -d %)
  [[ -z $level || $level -ge $floor ]] && exit 0
  print -u2 "$(date '+%H:%M') battery at $level%, under $floor%: waiting an hour"
  sleep 3600
done
