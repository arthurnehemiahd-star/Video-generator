"""
computer.py
-----------
The "Computer Assistant": can open applications — but ONLY ones you've
explicitly named in config.APPROVED_APPS. There is no general "run this
command" ability here on purpose. If it's not in the whitelist by name,
it does not run, full stop. This is the safety model, not a detail.

To allow an app, add it to APPROVED_APPS in ai_brain/config.py:
    APPROVED_APPS = {
        "notepad": r"C:\\Windows\\system32\\notepad.exe",
        "calculator": "gnome-calculator",
    }
Then `/open notepad` will work and nothing else will.
"""

import subprocess
from ai_brain import config


class AppNotApprovedError(Exception):
    pass


def list_approved() -> list[str]:
    return sorted(config.APPROVED_APPS.keys())


def open_app(name: str) -> str:
    name = name.strip().lower()
    if name not in config.APPROVED_APPS:
        approved = ", ".join(list_approved()) or "(none configured yet)"
        raise AppNotApprovedError(
            f"'{name}' is not in your approved apps list. "
            f"Approved: {approved}. Add it to APPROVED_APPS in ai_brain/config.py first."
        )

    target = config.APPROVED_APPS[name]
    try:
        subprocess.Popen(
            target if isinstance(target, list) else [target],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Configured path for '{name}' doesn't exist: {target}"
        )
    return f"Opened '{name}'."
