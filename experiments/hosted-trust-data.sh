#!/usr/bin/env zsh
# Rebuilds one book's trust data with Qwen read through OpenRouter (DeepInfra bf16), timed
# and detached in screen. Only for runs the user allowed hosted Qwen for.
#   experiments/hosted-trust-data.sh <name> <book> <pages> <label>
set -euo pipefail
name=$1 book=$2 pages=$3 label=$4
[[ -f golden/${book%%--*}/manifest.toml || $book == stella ]] || { print -u2 "unknown book: $book"; exit 1; }
exec experiments/detached.sh $name zsh -c "set -a; source ~/.openrouter.env; set +a
export OPENROUTER_API_KEY=\$KEY ROBO_READ_VIA=openrouter:qwen/qwen3.8-27b@deepinfra/bf16
experiments/timed.sh ${(q)label} $pages work/probes/ocr-trust/logs/$name.log \
  uv run python experiments/ocr_trust_data.py --rebuild $book"
