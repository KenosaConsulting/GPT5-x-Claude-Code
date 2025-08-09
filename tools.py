from __future__ import annotations
import os, subprocess
from typing import Dict, Any
from pathlib import Path

ALLOWED_PREFIXES = [
    "pytest",
    "python -m pytest",
    "pip install -r requirements.txt",
    "ruff",
    "black",
    "mypy",
    "npm install",
    "npm test",
]

def repo_root() -> Path:
    root = os.environ.get("AIDEV_REPO") or os.getcwd()
    return Path(root).resolve()

def jail_path(p: str) -> Path:
    base = repo_root()
    target = (base / p).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError("Path escapes repo jail")
    return target

def read_file(path: str) -> Dict[str, Any]:
    fp = jail_path(path)
    if not fp.exists():
        return {"ok": False, "error":"file not found"}
    return {"ok": True, "path": str(fp.relative_to(repo_root())), "content": fp.read_text(encoding="utf-8")}

def write_file(path: str, content: str) -> Dict[str, Any]:
    fp = jail_path(path)
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(fp.relative_to(repo_root())), "bytes": len(content.encode("utf-8"))}

def bash(command: str, timeout: int = 90) -> Dict[str, Any]:
    command = command.strip()
    if not any(command.startswith(p) for p in ALLOWED_PREFIXES):
        return {"ok": False, "error": f"command not allowed: {command}"}
    try:
        proc = subprocess.run(
            command, shell=True, cwd=str(repo_root()),
            capture_output=True, text=True, timeout=timeout
        )
        return {"ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": proc.stdout[-8000:],
                "stderr": proc.stderr[-8000:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error":"timeout"}

def git_diff() -> Dict[str, Any]:
    proc = subprocess.run(
        "git diff", shell=True, cwd=str(repo_root()),
        capture_output=True, text=True, timeout=20
    )
    return {"ok": True, "diff": proc.stdout}

def git_apply(patch: str) -> Dict[str, Any]:
    proc = subprocess.run(
        "git apply --cached -", input=patch, shell=True, cwd=str(repo_root()),
        capture_output=True, text=True, timeout=20
    )
    if proc.returncode != 0:
        return {"ok": False, "error": proc.stderr}
    return {"ok": True, "message":"patch staged (index). Run `git commit` manually."}
