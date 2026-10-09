"""Gather everything for a period and fold it into per-project summaries."""

from __future__ import annotations

import fnmatch
import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .collectors import AGENT_COLLECTORS
from .collectors import git as gitc
from .models import Commit, Session
from .periods import Period


@dataclass
class Project:
    key: str
    name: str
    sessions: List[Session] = field(default_factory=list)
    commits: List[Commit] = field(default_factory=list)
    files: set = field(default_factory=set)
    minutes: int = 0

    @property
    def prompt_count(self) -> int:
        return sum(len(s.prompts) for s in self.sessions)

    @property
    def insertions(self) -> int:
        return sum(c.insertions for c in self.commits)

    @property
    def deletions(self) -> int:
        return sum(c.deletions for c in self.commits)


@dataclass
class Report:
    period: Period
    projects: List[Project]
    minutes: int
    minutes_by_day: Dict[date, int]
    sources: Dict[str, int]  # source -> number of sessions / commits found
    warnings: List[str] = field(default_factory=list)

    @property
    def commits(self) -> List[Commit]:
        return [c for p in self.projects for c in p.commits]

    @property
    def sessions(self) -> List[Session]:
        return [s for p in self.projects for s in p.sessions]


def _project_key(session: Session) -> str:
    """Prefer the git repo that most edited files live in, then the repo of the cwd."""
    votes: Counter = Counter()
    for _, f in session.files:
        top = gitc.toplevel(os.path.dirname(f))
        if top:
            votes[top] += 1
    if votes:
        return votes.most_common(1)[0][0]
    return gitc.toplevel(session.cwd) or session.cwd or "(unknown)"


def _excluded(path: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(path + "/", p) for p in patterns)


def _active_minutes(times: List[datetime], idle: int) -> int:
    """Sum the gaps between consecutive events, capping each at `idle` minutes.

    An isolated event still counts as a few minutes of work.
    """
    if not times:
        return 0
    times = sorted(times)
    total = 5.0
    for a, b in zip(times, times[1:]):
        gap = (b - a).total_seconds() / 60
        total += gap if gap <= idle else 5
    return int(round(total))


def build(period: Period, cfg: Dict[str, Any], only: Optional[List[str]] = None) -> Report:
    wanted = only or cfg["sources"]
    paths = cfg.get("paths") or {}
    sources: Dict[str, int] = {}
    warnings: List[str] = []
    sessions: List[Session] = []
    for name, fn in AGENT_COLLECTORS.items():
        if name not in wanted:
            continue
        root = paths.get(name)
        try:
            found = fn(period.start, period.end, Path(os.path.expanduser(root)) if root else None)
        except Exception as exc:  # one broken source must not sink the whole report
            warnings.append(f"{name}: {exc}")
            found = []
        sources[name] = len(found)
        sessions.extend(found)

    excludes = cfg.get("exclude") or []
    projects: Dict[str, Project] = {}

    def project(key: str) -> Project:
        if key not in projects:
            alias = (cfg.get("aliases") or {}).get(key)
            projects[key] = Project(key=key, name=alias or Path(key).name or key)
        return projects[key]

    for s in sessions:
        key = _project_key(s)
        if _excluded(key, excludes):
            continue
        p = project(key)
        p.sessions.append(s)
        p.files.update(f for _, f in s.files)

    if "git" in wanted:
        repos = {p.key for p in projects.values() if os.path.isdir(os.path.join(p.key, ".git"))
                 or os.path.isfile(os.path.join(p.key, ".git"))}
        repos.update(os.path.expanduser(r) for r in cfg.get("repos") or [])
        if cfg.get("scan_roots"):
            repos.update(gitc.discover_repos(cfg["scan_roots"]))
        authors = cfg.get("authors") or gitc.default_authors()
        if not authors:
            warnings.append("git: no author configured; set `authors` or `git config --global user.email`")
            commits = []
        else:
            commits = gitc.collect([r for r in repos if not _excluded(r, excludes)],
                                   period.start, period.end, authors)
        sources["git"] = len(commits)
        for c in commits:
            project(c.repo).commits.append(c)

    idle = int(cfg.get("idle_minutes") or 30)
    all_times: List[Tuple[datetime, str]] = []
    for p in projects.values():
        times = [t for s in p.sessions for t in s.times] + [c.time for c in p.commits]
        p.minutes = _active_minutes(times, idle)
        all_times.extend((t, p.key) for t in times)

    by_day: Dict[date, List[datetime]] = defaultdict(list)
    day_start = int(cfg.get("day_start_hour", 4))
    for t, _ in all_times:
        by_day[(t - timedelta(hours=day_start)).date()].append(t)
    minutes_by_day = {d: _active_minutes(by_day.get(d, []), idle) if by_day.get(d) else 0 for d in period.days}

    ordered = sorted(projects.values(), key=lambda p: (p.minutes, len(p.commits)), reverse=True)
    return Report(period, ordered, sum(minutes_by_day.values()), minutes_by_day, sources, warnings)


def to_dict(report: Report) -> Dict[str, Any]:
    """JSON-friendly view, used by `collect --json` and the LLM prompt."""
    per = report.period
    return {
        "period": {"kind": per.kind, "from": per.first_day.isoformat(), "to": per.last_day.isoformat(),
                   "window_start": per.start.isoformat(), "window_end": per.end.isoformat()},
        "totals": {
            "active_minutes_estimate": report.minutes,
            "projects": len(report.projects),
            "commits": len(report.commits),
            "insertions": sum(p.insertions for p in report.projects),
            "deletions": sum(p.deletions for p in report.projects),
            "agent_sessions": len(report.sessions),
            "prompts": sum(p.prompt_count for p in report.projects),
        },
        "minutes_by_day": {d.isoformat(): m for d, m in report.minutes_by_day.items()},
        "sources": report.sources,
        "warnings": report.warnings,
        "projects": [
            {
                "name": p.name,
                "path": p.key,
                "active_minutes_estimate": p.minutes,
                "commits": [
                    {"sha": c.sha, "time": c.time.isoformat(timespec="minutes"), "subject": c.subject,
                     "body": c.body, "insertions": c.insertions, "deletions": c.deletions,
                     "files_changed": c.files_changed}
                    for c in p.commits
                ],
                "agent_sessions": [
                    {"source": s.source, "title": s.title,
                     "first": min(s.times).isoformat(timespec="minutes"),
                     "last": max(s.times).isoformat(timespec="minutes"),
                     "prompts": [t for _, t in s.prompts],
                     "files_edited": sorted({_rel(f, p.key) for _, f in s.files})}
                    for s in sorted(p.sessions, key=lambda s: min(s.times))
                ],
            }
            for p in report.projects
        ],
    }


def _rel(path: str, root: str) -> str:
    try:
        return os.path.relpath(path, root) if path.startswith(root.rstrip("/") + "/") else path
    except ValueError:
        return path
