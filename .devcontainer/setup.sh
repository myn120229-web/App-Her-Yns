#!/usr/bin/env bash
set -e

echo "==> Installing Python dependencies"
pip install --no-cache-dir -r requirements.txt

echo "==> Installing Ollama"
curl -fsSL https://ollama.com/install.sh | sh

echo "==> Starting Ollama server in background to pull the model"
ollama serve > /tmp/ollama.log 2>&1 &
OLLAMA_PID=$!

# Wait for the server to come up
for i in $(seq 1 30); do
  if curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "==> Pulling model: qwen2.5:3b (small + capable, fits Codespaces free tier)"
ollama pull qwen2.5:3b || echo "Model pull failed — you can retry later with: ollama pull qwen2.5:3b"

kill $OLLAMA_PID 2>/dev/null || true

mkdir -p data
if [ ! -f data/profile.json ]; then
  cp app/profile.example.json data/profile.json
fi

echo "==> Setup complete. Run 'bash .devcontainer/start_ollama.sh' then 'streamlit run app.py' (this happens automatically on start)."
