#!/usr/bin/env zsh
# Runs a command in a detached screen session, so it outlives the terminal and the agent
# that started it. Its output goes to work/runs/<name>.out; `screen -ls` lists the runs,
# `screen -r robo-<name>` watches one (ctrl-a d leaves it running).
#   experiments/detached.sh <name> <command…>
set -euo pipefail
name=$1
shift
mkdir -p work/runs
screen -dmS "robo-$name" zsh -c "cd ${(q)PWD} && ${(j: :)${(q)@}} > work/runs/$name.out 2>&1"
print "robo-$name started; output in work/runs/$name.out"
