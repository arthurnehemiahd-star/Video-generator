"""
memory.py
---------
Very simple persistent chat history, stored as JSON on disk so your AI
remembers the current conversation across app restarts. This is separate
from any "project" data (trailers, music videos, etc.) which will live
under data/projects/.
"""

import json
from ai_brain import config


def load_history() -> list[dict]:
    if not config.HISTORY_FILE.exists():
        return []
    try:
        return json.loads(config.HISTORY_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def save_history(history: list[dict]) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.HISTORY_FILE.write_text(json.dumps(history, indent=2))


def append_message(history: list[dict], role: str, content: str) -> list[dict]:
    history.append({"role": role, "content": content})
    save_history(history)
    return history


def clear_history() -> list[dict]:
    save_history([])
    return []
