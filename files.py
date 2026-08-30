"""
files.py
--------
The "File Assistant": lets the AI/commands create, rename, move, and
delete files — but ONLY inside data/projects/. This sandboxing is the
whole safety model: no path outside PROJECTS_DIR is ever touched, no
matter what string comes in. Every public function resolves and checks
the path before doing anything.
"""

from pathlib import Path
from ai_brain import config


class UnsafePathError(Exception):
    """Raised when a requested path would land outside the sandbox."""


def _resolve_safe(relative_path: str) -> Path:
    """
    Resolves a user-given relative path against PROJECTS_DIR and refuses
    anything that would escape it (via '..', absolute paths, symlinks).
    """
    base = config.PROJECTS_DIR.resolve()
    base.mkdir(parents=True, exist_ok=True)
    candidate = (base / relative_path).resolve()
    if base not in candidate.parents and candidate != base:
        raise UnsafePathError(
            f"'{relative_path}' would resolve outside the projects folder — refused."
        )
    return candidate


def list_files(relative_dir: str = "") -> list[str]:
    target = _resolve_safe(relative_dir)
    if not target.exists():
        return []
    return sorted(
        f"{p.name}/" if p.is_dir() else p.name
        for p in target.iterdir()
    )


def create_file(relative_path: str, content: str = "") -> Path:
    target = _resolve_safe(relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"'{relative_path}' already exists.")
    target.write_text(content)
    return target


def make_folder(relative_path: str) -> Path:
    target = _resolve_safe(relative_path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def rename(relative_path: str, new_name: str) -> Path:
    target = _resolve_safe(relative_path)
    if not target.exists():
        raise FileNotFoundError(f"'{relative_path}' doesn't exist.")
    if "/" in new_name or "\\" in new_name:
        raise UnsafePathError("New name can't contain path separators.")
    destination = _resolve_safe(str(Path(relative_path).parent / new_name))
    target.rename(destination)
    return destination


def move(relative_path: str, new_relative_path: str) -> Path:
    source = _resolve_safe(relative_path)
    destination = _resolve_safe(new_relative_path)
    if not source.exists():
        raise FileNotFoundError(f"'{relative_path}' doesn't exist.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source.rename(destination)
    return destination


def delete(relative_path: str, confirm: bool = False) -> None:
    if not confirm:
        raise PermissionError(
            "Refusing to delete without explicit confirmation "
            "(pass confirm=True)."
        )
    target = _resolve_safe(relative_path)
    if not target.exists():
        raise FileNotFoundError(f"'{relative_path}' doesn't exist.")
    if target.is_dir():
        import shutil
        shutil.rmtree(target)
    else:
        target.unlink()
