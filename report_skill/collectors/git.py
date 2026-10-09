"""Git history: your own commits in repos you worked in during the window."""

from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from ..models import Commit
from ..util import parse_iso, redact

_REC, _FLD = "\x1e", "\x1f"
_STAT = re.compile(r"(\d+) files? changed(?:, (\d+) insertions?\(\+\))?(?:, (\d+) deletions?\(-\))?")
_toplevel_cache: Dict[str, Optional[str]] = {}


def _git(args: List[str], cwd: Optional[str] = None, timeout: int = 30) -> Optional[str]:
    try:
        r = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


def toplevel(path: str) -> Optional[str]:
    """Resolve any directory to the root of the git repo containing it."""
    if not path:
        return None
    if path in _toplevel_cache:
        return _toplevel_cache[path]
    result = None
    if os.path.isdir(path):
        out = _git(["rev-parse", "--path-format=absolute", "--show-toplevel", "--git-common-dir"],
                   cwd=path, timeout=5)
        lines = out.split("\n") if out else []
        if lines and lines[0].strip():
            result = lines[0].strip()
            # Fold linked worktrees into their main checkout so commits are not counted twice.
            common = lines[1].strip() if len(lines) > 1 else ""
            if common.endswith("/.git") and os.path.isdir(common):
                result = os.path.dirname(common)
    _toplevel_cache[path] = result
    return result


def default_authors() -> List[str]:
    authors = []
    for key in ("user.email", "user.name"):
        out = _git(["config", "--global", key], timeout=5)
        if out and out.strip():
            authors.append(out.strip())
    return authors


def discover_repos(roots: Iterable[str], max_depth: int = 3) -> Set[str]:
    """Find git repos under the given directories without descending into them."""
    found: Set[str] = set()
    skip = {"node_modules", ".venv", "venv", "vendor", "dist", "build", "target", ".cache"}
    for root in roots:
        root = os.path.expanduser(root)
        base_depth = root.rstrip("/").count("/")
        for dirpath, dirnames, _ in os.walk(root):
            if ".git" in dirnames or os.path.isfile(os.path.join(dirpath, ".git")):
                found.add(dirpath)
                dirnames[:] = []
                continue
            if dirpath.count("/") - base_depth >= max_depth:
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in skip]
    return found


def log(repo: str, start: datetime, end: datetime, authors: List[str]) -> List[Commit]:
    fmt = _REC + _FLD.join(["%H", "%aI", "%s", "%b", "%D"]) + _FLD
    args = [
        "log", "--all", "--no-merges", f"--since={start.isoformat()}", f"--until={end.isoformat()}",
        f"--pretty=format:{fmt}", "--shortstat",
    ]
    args += [f"--author={a}" for a in authors]
    out = _git(args, cwd=repo)
    if not out:
        return []
    commits = []
    for chunk in out.split(_REC)[1:]:
        parts = chunk.split(_FLD)
        if len(parts) < 6:
            continue
        sha, date, subject, body, refs, tail = parts[:6]
        ts = parse_iso(date)
        if ts is None or not (start <= ts < end):
            continue
        c = Commit(repo=repo, sha=sha[:10], time=ts, subject=redact(subject.strip()),
                   body=redact(body.strip())[:500], refs=refs.strip())
        m = _STAT.search(tail)
        if m:
            c.files_changed = int(m.group(1))
            c.insertions = int(m.group(2) or 0)
            c.deletions = int(m.group(3) or 0)
        commits.append(c)
    return commits


def collect(repos: Iterable[str], start: datetime, end: datetime, authors: List[str]) -> List[Commit]:
    commits: List[Commit] = []
    seen = set()
    for repo in sorted(set(repos)):
        if not Path(repo).exists():
            continue
        for c in log(repo, start, end, authors):
            if (c.repo, c.sha) not in seen:
                seen.add((c.repo, c.sha))
                commits.append(c)
    return sorted(commits, key=lambda c: c.time)
