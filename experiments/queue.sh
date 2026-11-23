#!/usr/bin/env zsh
# The machine's job queue: Pueue decides when a run starts, by the resource it needs, first
# come first served; the run itself still goes through detached.sh (a robo-<name> screen,
# output in work/runs/<name>.out), so priority.first, the battery guard and stop-run.sh work
# on it unchanged. Groups and how many of each run at once:
#   gpu 1       anything that asks a model (Ollama, Kapitsa, a model's own server)
#   cpu 1       many-core work without a model: an arbiter training, a warm bench
#   download 1  a model download (the line is slow; two at once only slow both)
#   light 4     small work that asks no model and uses a core or two
# A step needing a model and many cores goes in gpu and takes work/runs/cpu-heavy.lock inside.
#   experiments/queue.sh add <group> <name> [--after <id>]… -- <command…>   prints the job id
#   experiments/queue.sh status                                              `pueue status`
#   experiments/queue.sh stop <id>                                           stops a job's run
# Stop a running job with `queue.sh stop` (or stop-run.sh <name>), never `pueue kill`: Pueue
# kills only the waiting process (SIGKILL), and the robo- screen goes on. `pueue remove <id>`
# drops a job not yet started; `pueue log <id>` shows how a job ended.
set -euo pipefail
cd "${0:A:h}/.."
typeset -A LIMITS=(gpu 1 cpu 1 download 1 light 4)

daemon() {  # the daemon, in a screen named pueued (not robo-: pausing for the user leaves it be)
  if ! pueue status >/dev/null 2>&1; then
    { screen -ls || true; } | grep -q "\.pueued[[:space:]]" || screen -dmS pueued pueued
    for _ in {1..30}; do pueue status >/dev/null 2>&1 && break; sleep 1; done
    pueue status >/dev/null 2>&1 || { print -u2 "pueued did not start"; exit 1; }
  fi
  local have=$(pueue group 2>/dev/null)
  for g n in ${(kv)LIMITS}; do
    [[ $have == *"Group \"$g\""* ]] || pueue group add $g >/dev/null
    pueue parallel $n -g $g >/dev/null
  done
}

case ${1:-} in
  add)
    group=$2 name=$3; shift 3
    [[ -n ${LIMITS[$group]:-} ]] || { print -u2 "groups: ${(k)LIMITS}"; exit 1; }
    after=()
    while [[ ${1:-} == --after ]]; do after+=(--after $2); shift 2; done
    [[ ${1:-} == -- ]] && shift
    (( $# )) || { print -u2 "no command"; exit 1; }
    # The header lines detached.sh demands; it checks the models are pulled when the job starts.
    for arg in "$@"; do
      [[ $arg == *.sh && -f $arg ]] || continue
      for field in resumes models; do
        grep -q "^# $field: ." $arg || { print -u2 "$arg has no '# $field:' line"; exit 1; }
      done
      zsh -n $arg
    done
    daemon
    pueue add --print-task-id -g $group -l $name $after -- \
      "experiments/queue.sh run ${(q)name} ${(j: :)${(q)@}}"
    ;;
  run)  # what Pueue runs: the command in its robo- screen, waited for, its exit code returned
    name=$2; shift 2
    trap 'experiments/stop-run.sh $name >/dev/null 2>&1; exit 143' TERM INT
    experiments/detached.sh $name "$@"
    while { screen -ls || true; } | grep -q "\.robo-${name}[[:space:]]"; do sleep 10 & wait $!; done
    tail -3 work/runs/$name.out 2>/dev/null || true
    exit $(cat work/runs/$name.exit 2>/dev/null || print 1)
    ;;
  stop)  # a running job: its robo- screen and everything under it; the waiting task then ends
    label=$(pueue status --json | python3 -I -c 'import json,sys; print(json.load(sys.stdin)["tasks"][sys.argv[1]]["label"] or "")' $2)
    [[ -n $label ]] || { print -u2 "job $2 has no label"; exit 1; }
    experiments/stop-run.sh $label
    ;;
  status)
    daemon
    pueue status
    ;;
  *)
    sed -n '2,19p' $0
    exit 1
    ;;
esac
