"""Restricted tool catalogue: read-only repo/log/test/health first."""
from __future__ import annotations
import os
import subprocess

def _contained(root: str, p: str) -> str:
    ap = os.path.abspath(p if os.path.isabs(p) else os.path.join(root, p))
    r = os.path.abspath(root)
    if not (ap == r or ap.startswith(r + os.sep)):
        raise ValueError(f"path escape refused: {p!r}")
    return ap

def repo_status(repo: str) -> dict:
    repo = _contained(repo, ".")
    def run(*a):
        return subprocess.run(a, cwd=repo, capture_output=True, text=True, timeout=30)
    br = run("git", "branch", "--show-current")
    st = run("git", "status", "--short", "--branch")
    unpushed = run("git", "log", "--oneline", "@{upstream}..HEAD", "--max-count=20")
    return {"branch": br.stdout.strip(), "status": st.stdout.strip()[:4000],
            "unpushed": unpushed.stdout.strip()[:4000]}

def repo_branches(repo: str) -> dict:
    repo = _contained(repo, ".")
    r = subprocess.run(["git", "branch", "-vv"], cwd=repo, capture_output=True,
                       text=True, timeout=30)
    stale = subprocess.run(["git", "branch", "--no-merged", "main"], cwd=repo,
                           capture_output=True, text=True, timeout=30)
    return {"branches": r.stdout.strip()[:4000], "unmerged_vs_main": stale.stdout.strip()[:2000],
            "recommendation": "recommend only; no destructive cleanup"}

def log_tail(path: str, root: str, n: int = 60) -> dict:
    ap = _contained(root, path)
    with open(ap, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()[-max(1, min(n, 200)):]
    return {"path": ap, "lines": "".join(lines)[-8000:]}

def health_check() -> dict:
    import shutil
    total, used, free = shutil.disk_usage(os.path.expanduser("~"))
    return {"disk_free_gb": round(free / 1e9, 1), "ok": free > 5e9}
