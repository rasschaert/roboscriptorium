#!/usr/bin/env zsh
# Runs a command in a detached screen session, so it outlives the terminal and the agent
# that started it. Its output goes to work/runs/<name>.out; `screen -ls` lists the runs,
# `screen -r robo-<name>` watches one (ctrl-a d leaves it running).
# An agent pairs it with a watcher it can lose: a background
#   while screen -ls | grep -q "\.robo-<name>[[:space:]]"; do sleep 30; done
# which ends, and so notifies, when the run does. The pattern matches the whole name:
# `screen -ls robo-<name>` matches by prefix, so robo-<name>-2 would keep it going.
#   experiments/detached.sh <name> <command…>
set -euo pipefail
name=$1
shift
if screen -ls | grep -q "\.robo-$name[[:space:]]"; then
  print -u2 "robo-$name is already running"
  exit 1
fi
mkdir -p work/runs
screen -dmS "robo-$name" zsh -c "cd ${(q)PWD} && ${(j: :)${(q)@}} > work/runs/$name.out 2>&1"
print "robo-$name started; output in work/runs/$name.out"
