#!/usr/bin/env zsh
# Serves an imajev size with llama.cpp on Ollama's own blobs (weights and projector), for
# `clients/llama.py`: last-token hidden states, the image in the prompt.
#   experiments/llama-serve.sh <2b|4b|9b> [port]      (default port 8092, ROBO_LLAMA_URL's)
set -euo pipefail
size=$1 port=${2:-8092}
blobs=(${(f)"$(ollama show hf.co/mindchain/imajev-$size-GGUF:Q8_0 --modelfile | awk '/^FROM/ {print $2}')"})
(( ${#blobs} == 2 )) || { print -u2 "expected a model and a projector blob, got: $blobs"; exit 1; }
exec llama-server -m $blobs[1] --mmproj $blobs[2] --embeddings --pooling last \
  --embd-normalize -1 --port $port -ngl 99 -c 4096
