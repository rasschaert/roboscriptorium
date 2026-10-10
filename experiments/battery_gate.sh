#!/usr/bin/env zsh
# Waits while the battery is below 30%, checking every hour: Ollama drains it even on
# the charger. Every model run starts through it (`timed.sh` calls it first).
set -uo pipefail
floor=${ROBO_BATTERY_FLOOR:-30}
while true; do
  level=$(pmset -g batt | grep -oE '[0-9]+%' | head -1 | tr -d %)
  [[ -z $level || $level -ge $floor ]] && exit 0
  print -u2 "$(date '+%H:%M') battery at $level%, under $floor%: waiting an hour"
  sleep 3600
done
