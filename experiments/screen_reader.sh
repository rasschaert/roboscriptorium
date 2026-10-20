#!/usr/bin/env zsh
# Screens a reader candidate on the frozen reader set: its own score, then the vote
# simulation beside qwen3.8 and glm-ocr. Record the numbers in docs/models.md and
# docs/decisions.md.
#   experiments/screen_reader.sh <label> <MLX model dir> [prompt]   # an MLX model
#   experiments/screen_reader.sh <ollama model>                     # an Ollama model
set -euo pipefail
cd "${0:A:h:h}"
if [[ $# -ge 2 ]]; then
  label=$1 dir=$2
  work/models/mlx-env/bin/python -I experiments/mlx_read_set.py "$dir" "$label" "${3:-}"
else
  label=$1
fi
uv run python experiments/tryout.py run reader "$label"
stem=${label//:/_}
stem=${stem//\//_}
uv run python experiments/vote_sim.py "$stem"
