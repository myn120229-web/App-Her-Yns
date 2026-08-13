"""
Wrapper around any OpenAI-compatible Chat Completions API.

Supports:
- Local Ollama (default, http://127.0.0.1:11434/v1)
- Any hosted OpenAI-compatible endpoint (Zyloo, OpenAI, etc.)

Endpoint + key + model are configurable at runtime via the Telegram bot
(/setapi, /setmodel) and persisted to data/llm_config.json so the user can
point the app at any provider they like.
"""
from __future__ import annotations

import json
import os
import re
import requests
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "llm_config.json"

DEFAULTS = {
    "base_url": os.environ.get("LLM_BASE_URL", "http://127.0.0.1:11434/v1"),
    "api_key": os.environ.get("LLM_API_KEY", "ollama"),
    "model": os.environ.get("UNEMPLOYED_MODEL", "qwen2.5:3b"),
}


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            return {**DEFAULTS, **saved}
        except Exception:
            pass
    return dict(DEFAULTS)


def _save_config(cfg: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    tmp.replace(CONFIG_PATH)


def get_config() -> dict:
    return _load_config()


def set_config(base_url: str, api_key: str, model: str):
    cfg = {"base_url": base_url, "api_key": api_key, "model": model}
    _save_config(cfg)
    return cfg


def is_available() -> bool:
    cfg = _load_config()
    try:
        r = requests.get(f"{cfg['base_url'].rstrip('/')}/models",
                         headers={"Authorization": f"Bearer {cfg['api_key']}"},
                         timeout=5)
        return r.status_code in (200, 401)  # 401 still means the endpoint is up
    except requests.RequestException:
        # Ollama's /models may not exist; fall back to a chat probe
        try:
            chat("You are a test.", "reply ok", temperature=0)
            return True
        except Exception:
            return False


def _extract_json(text: str) -> dict | list:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text.strip())
    text = re.sub(r"```$", "", text.strip())
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
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
    cfg = _load_config()
    url = f"{cfg['base_url'].rstrip('/')}/chat/completions"
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "stream": False,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"},
        json=payload,
        timeout=180,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


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
