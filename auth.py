"""
auth.py
-------
Simple password gate for private hosting. The password is never stored
in plain text — you set ACCESS_PASSWORD once via `python -m ai_brain.auth
set`, which hashes it with a per-install random salt and writes the hash
to .env. From then on, .env only ever contains the hash, never the
password itself.

If ACCESS_PASSWORD_HASH isn't set in .env at all, auth is considered
"not configured" and both the CLI and web app run open — that's the
right default for a first run on your own machine, and you turn it on
deliberately when you're ready to host this somewhere reachable by
others.
"""

import hashlib
import os
import secrets
import sys
from ai_brain import config


def is_configured() -> bool:
    return bool(os.environ.get("ACCESS_PASSWORD_HASH"))


def _hash(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode()).hexdigest()


def set_password(password: str) -> None:
    """Hashes and saves a new password into .env, replacing any existing one."""
    salt = secrets.token_hex(16)
    hashed = _hash(password, salt)

    lines = []
    if config.ENV_PATH.exists():
        lines = [
            l for l in config.ENV_PATH.read_text().splitlines()
            if not l.startswith("ACCESS_PASSWORD_HASH=")
            and not l.startswith("ACCESS_PASSWORD_SALT=")
        ]
    lines.append(f"ACCESS_PASSWORD_SALT={salt}")
    lines.append(f"ACCESS_PASSWORD_HASH={hashed}")
    config.ENV_PATH.write_text("\n".join(lines) + "\n")
    print(f"Password saved (hashed) to {config.ENV_PATH}")


def verify(password: str) -> bool:
    stored_hash = os.environ.get("ACCESS_PASSWORD_HASH", "")
    salt = os.environ.get("ACCESS_PASSWORD_SALT", "")
    if not stored_hash:
        return True  # auth not configured — open by default, see module docstring
    return secrets.compare_digest(_hash(password, salt), stored_hash)


def prompt_and_verify(max_attempts: int = 3) -> bool:
    """For CLI use: prompts for a password if one is configured. Returns
    True if access should proceed (either no password configured, or a
    correct one was entered within max_attempts)."""
    if not is_configured():
        return True

    import getpass
    for attempt in range(max_attempts):
        pw = getpass.getpass("Password: ")
        if verify(pw):
            return True
        print(f"Incorrect password. {max_attempts - attempt - 1} attempts left.")
    return False


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "set":
        import getpass
        pw = getpass.getpass("New password: ")
        confirm = getpass.getpass("Confirm password: ")
        if pw != confirm:
            print("Passwords didn't match.")
            sys.exit(1)
        set_password(pw)
    else:
        print("Usage: python -m ai_brain.auth set")
