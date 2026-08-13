#!/usr/bin/env bash
# Runs on every codespace start (postStartCommand). Starts Ollama in the
# background if it isn't already running, then leaves it there so the
# Streamlit app can call http://127.0.0.1:11434.

if ! curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
  nohup ollama serve > /tmp/ollama.log 2>&1 &
  echo "Started Ollama server."
else
  echo "Ollama already running."
fi
