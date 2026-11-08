#!/usr/bin/env zsh
# Restarts the Ollama app (the user's standing permission, 2026-11-08): asks it to quit,
# kills it if it won't, reopens it and waits until the API answers. A run's clients retry
# dropped connections and every answer is cached, so a run in flight resumes.
#   experiments/ollama-restart.sh
set -uo pipefail
osascript -e 'quit app "Ollama"' 2>/dev/null
for _ in {1..10}; do pgrep -f "Ollama.app/Contents/Resources/ollama serve" >/dev/null || break; sleep 1; done
if pgrep -f "Ollama.app" >/dev/null; then
  pkill -f "Ollama.app/Contents/MacOS/Ollama"
  pkill -f "Ollama.app/Contents/Resources/ollama"
  sleep 3
  pkill -9 -f "Ollama.app" 2>/dev/null
fi
open -a Ollama
for _ in {1..60}; do
  if curl -s -m 2 http://127.0.0.1:11434/api/version >/dev/null; then
    echo "ollama up: $(curl -s -m 2 http://127.0.0.1:11434/api/version)"
    exit 0
  fi
  sleep 2
done
echo "ollama did not come back within 2 minutes" >&2
exit 1
