"""Server-side skill file storage.

Custom/hub skill code is saved as python files under SKILLS_DIR
(default: <backend>/skills). The DB mirrors the code for fast exec.
"""
import os
import re

SKILLS_DIR = os.path.abspath(os.environ.get(
    "SKILLS_DIR", os.path.join(os.path.dirname(__file__), "..", "skills")))


def _safe_name(name: str) -> str:
    base = re.sub(r"[^A-Za-z0-9_\-]", "_", name or "").strip("_")
    return base or "skill"


def skill_file_path(name: str) -> str:
    return os.path.join(SKILLS_DIR, f"{_safe_name(name)}.py")


def save_skill_file(name: str, code: str) -> str:
    """Write skill code to its server file; returns the path."""
    os.makedirs(SKILLS_DIR, exist_ok=True)
    path = skill_file_path(name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code or "")
    return path


def read_skill_file(name: str) -> str | None:
    path = skill_file_path(name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def delete_skill_file(name: str) -> None:
    path = skill_file_path(name)
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
