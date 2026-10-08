#!/usr/bin/env zsh
# Runs a command and appends how long it took to docs/run-times.md.
#   experiments/timed.sh "<what, and how warm the caches were>" <pages> <log> <command…>
set -uo pipefail
label=$1 pages=$2 log=$3
shift 3
start=$(date +%s)
"$@" > "$log" 2>&1
code=$?
minutes=$(( ($(date +%s) - start + 30) / 60 ))
print "| $(date '+%Y-%m-%d') | $label | $pages | $minutes | $code |" >> docs/run-times.md
exit $code
