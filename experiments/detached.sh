#!/usr/bin/env zsh
# Runs a command in a detached screen session, so it outlives the terminal and the agent
# that started it. Its output goes to work/runs/<name>.out; `screen -ls` lists the runs,
# `screen -r robo-<name>` watches one (ctrl-a d leaves it running), and
# `experiments/stop-run.sh <name>` stops one with everything it started.
# An agent pairs it with a watcher it can lose: a background
#   while screen -ls | grep -q "\.robo-<name>[[:space:]]"; do sleep 30; done
# which ends, and so notifies, when the run does. The pattern matches the whole name:
# `screen -ls robo-<name>` matches by prefix, so robo-<name>-2 would keep it going.
#   experiments/detached.sh <name> <command…>
set -euo pipefail
name=$1
shift
# `screen -ls` exits 1 when sessions exist, which pipefail would take for no match.
if { screen -ls || true; } | grep -q "\.robo-${name}[[:space:]]"; then
  print -u2 "robo-$name is already running"
  exit 1
fi
# A run script says, in comments, what a stop costs and what it loads, or it doesn't start:
#   # resumes: <what is kept as it goes, and what a stop loses>
#   # models: <the Ollama models it asks, comma-separated; "none" for none>
#   # one at a time: <how it keeps them from swapping>   (needed past 48 GB together)
for arg in "$@"; do
  [[ $arg == *.sh && -f $arg ]] || continue
  for field in resumes models; do
    grep -q "^# $field: ." $arg || {
      print -u2 "$arg has no '# $field:' line. Before queuing, find out and write down:"
      print -u2 "  # resumes: what the run keeps as it goes, and what a stop loses"
      print -u2 "  # models: the Ollama models it asks (or none)"
      exit 1
    }
  done
  total=0
  for model in ${(s:,:)"$(grep -m1 '^# models: ' $arg | cut -c11-)"}; do
    model=${model// /}
    [[ $model == none ]] && continue
    size=$(ollama list 2>/dev/null | awk -v m=$model '$1 == m && $4 == "GB" {print int($3 + 0.5)}')
    [[ -n $size ]] || { print -u2 "$arg: model $model is not in 'ollama list' (or under 1 GB: leave it out)"; exit 1; }
    (( total += size ))
  done
  if (( total > 48 )) && ! grep -q "^# one at a time: ." $arg; then
    print -u2 "$arg asks $total GB of models, more than fit together beside a build."
    print -u2 "Say how it keeps them from swapping at every question: # one at a time: …"
    exit 1
  fi
done
mkdir -p work/runs
# The command's exit code lands in work/runs/<name>.exit (experiments/queue.sh reads it).
rm -f work/runs/$name.exit
screen -dmS "robo-$name" zsh -c "cd ${(q)PWD} && ${(j: :)${(q)@}} > work/runs/$name.out 2>&1; print \$? > work/runs/$name.exit"
print "robo-$name started; output in work/runs/$name.out"
