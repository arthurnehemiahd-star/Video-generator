"""
config.py
---------
Central place for settings. Loads secrets from a local .env file so you
never hardcode API keys into your source code (and never commit them).

To use:
1. Copy `.env.example` to `.env`
2. Fill in your ANTHROPIC_API_KEY (or swap in another provider's key)
"""

import os
from pathlib import Path

# --- Load .env manually (no extra dependency required) -------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

_load_env_file(ENV_PATH)

# --- Settings --------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
AI_MODEL = os.environ.get("AI_MODEL", "claude-sonnet-5")

ASSISTANT_NAME = os.environ.get("ASSISTANT_NAME", "My AI")

DATA_DIR = PROJECT_ROOT / "data"
PROJECTS_DIR = DATA_DIR / "projects"
HISTORY_FILE = DATA_DIR / "chat_history.json"

# Approved apps/folders the Computer Assistant is allowed to touch.
# Nothing gets opened unless its name is explicitly listed here — this
# is the entire safety model for /open, so keep it deliberate.
# Examples (edit for your OS/apps):
APPROVED_APPS = {
    # Windows:
    # "notepad": r"C:\Windows\system32\notepad.exe",
    # "calculator": r"C:\Windows\system32\calc.exe",
    # macOS (use 'open -a'):
    # "textedit": ["open", "-a", "TextEdit"],
    # "calculator": ["open", "-a", "Calculator"],
    # Linux:
    # "text_editor": "gedit",
    # "calculator": "gnome-calculator",
}
