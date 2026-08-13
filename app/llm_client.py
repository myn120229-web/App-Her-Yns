"""
Wrapper around a local Ollama server (http://127.0.0.1:11434).

Everything in this app that needs the model goes through here so there's
one place that: picks the model, forces JSON output when we need structured
data back, retries on malformed JSON, and fails loudly rather than silently
if Ollama isn't running.
"""
from __future__ import annotations

import json
import os
import re
import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("UNEMPLOYED_MODEL", "qwen2.5:3b")


class OllamaNotRunning(Exception):
    pass


def is_available() -> bool:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        return r.status_code == 200
    except requests.RequestException:
        return False


def _extract_json(text: str) -> dict | list:
    """Models sometimes wrap JSON in prose or code fences. Pull the first
    {...} or [...] block out and parse it."""
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text.strip())
    text = re.sub(r"```$", "", text.strip())
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fall back to grabbing the largest {...} or [...] span.
    for open_c, close_c in [("{", "}"), ("[", "]")]:
        start = text.find(open_c)
        end = text.rfind(close_c)
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    raise ValueError(f"Could not parse JSON from model output:\n{text[:500]}")


def chat(system: str, user: str, json_mode: bool = False, temperature: float = 0.2) -> str:
    if not is_available():
        raise OllamaNotRunning(
            "Ollama isn't responding on 127.0.0.1:11434. In the Codespace terminal run: "
            "bash .devcontainer/start_ollama.sh"
        )
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": temperature},
    }
    if json_mode:
        payload["format"] = "json"

    r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=180)
    r.raise_for_status()
    return r.json()["message"]["content"]


def chat_json(system: str, user: str, temperature: float = 0.2, retries: int = 2) -> dict | list:
    last_err = None
    for attempt in range(retries + 1):
        raw = chat(system, user, json_mode=True, temperature=temperature)
        try:
            return _extract_json(raw)
        except ValueError as e:
            last_err = e
            user = user + "\n\nYour previous reply was not valid JSON. Reply with ONLY valid JSON, no prose, no markdown fences."
    raise last_err
