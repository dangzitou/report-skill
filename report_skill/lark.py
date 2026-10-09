"""Lark / Feishu adapter built on the official lark-cli (https://github.com/larksuite/cli).

Two directions:
  * collect: meetings from your calendar, tasks you completed, tasks coming due
  * publish: send the report as a message, or save it as a Lark doc

Nothing here talks to Lark directly; every call shells out to `lark-cli`, which
keeps your credentials in the OS keychain.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .util import parse_iso, redact

BIN = "lark-cli"
DECLINED = {"decline", "declined"}


class LarkError(RuntimeError):
    pass


@dataclass
class Meeting:
    summary: str
    start: datetime
    end: Optional[datetime] = None
    rsvp: str = ""

    @property
    def minutes(self) -> int:
        if not self.end:
            return 0
        return max(0, int((self.end - self.start).total_seconds() // 60))


@dataclass
class Task:
    summary: str
    url: str = ""
    completed_at: Optional[datetime] = None
    due_at: Optional[datetime] = None


@dataclass
class LarkActivity:
    meetings: List[Meeting] = field(default_factory=list)
    tasks_done: List[Task] = field(default_factory=list)
    tasks_open: List[Task] = field(default_factory=list)

    @property
    def meeting_minutes(self) -> int:
        return sum(m.minutes for m in self.meetings)

    def __bool__(self) -> bool:
        return bool(self.meetings or self.tasks_done or self.tasks_open)


def available() -> bool:
    return shutil.which(BIN) is not None


def run(args: List[str], timeout: int = 60) -> Any:
    """Run lark-cli with JSON output and return the `data` field of its success envelope."""
    try:
        proc = subprocess.run([BIN, *args, "--format", "json"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout)
    except FileNotFoundError:
        raise LarkError("lark-cli not found; install with `npx @larksuite/cli@latest install`")
    except subprocess.TimeoutExpired:
        raise LarkError(f"lark-cli {' '.join(args[:2])} timed out")
    out = proc.stdout.strip()
    try:
        env = json.loads(out) if out else {}
    except json.JSONDecodeError:
        env = {}
    if proc.returncode != 0 or env.get("ok") is False:
        msg = _error_message(proc.stderr) or out[-300:] or f"exit {proc.returncode}"
        raise LarkError(msg)
    return env.get("data", env)


def _error_message(stderr: str) -> str:
    text = (stderr or "").strip()
    try:
        err = json.loads(text).get("error") or {}
        msg = err.get("message", "")
        hint = err.get("hint", "")
        return f"{msg} ({hint})" if hint else msg
    except (ValueError, AttributeError):
        return text.splitlines()[-1][:300] if text else ""


def _event_time(obj: Any) -> Optional[datetime]:
    if not isinstance(obj, dict):
        return None
    if obj.get("datetime"):
        return parse_iso(obj["datetime"])
    if obj.get("timestamp"):
        try:
            return datetime.fromtimestamp(int(obj["timestamp"])).astimezone()
        except (TypeError, ValueError):
            return None
    if obj.get("date"):  # all-day event
        return parse_iso(obj["date"] + "T00:00:00")
    return None


def _items(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("items", "events", "list"):
            if isinstance(data.get(key), list):
                return [x for x in data[key] if isinstance(x, dict)]
    return []


def _task(item: Dict[str, Any]) -> Task:
    return Task(summary=redact(str(item.get("summary") or "").strip()), url=item.get("url") or "",
                completed_at=parse_iso(item.get("completed_at") or ""), due_at=parse_iso(item.get("due_at") or ""))


def meetings(start: datetime, end: datetime, identity: str = "user") -> List[Meeting]:
    data = run(["calendar", "+agenda", "--as", identity,
                "--start", start.isoformat(timespec="seconds"),
                "--end", (end - timedelta(seconds=1)).isoformat(timespec="seconds")])
    out = []
    for e in _items(data):
        if str(e.get("self_rsvp_status", "")).lower() in DECLINED:
            continue
        s = _event_time(e.get("start_time")) or parse_iso(str(e.get("start", "")))
        if not s:
            continue
        out.append(Meeting(summary=redact(str(e.get("summary") or "(untitled)").strip()), start=s,
                           end=_event_time(e.get("end_time")) or parse_iso(str(e.get("end", ""))),
                           rsvp=str(e.get("self_rsvp_status", ""))))
    return sorted(out, key=lambda m: m.start)


def tasks_done(start: datetime, end: datetime, identity: str = "user") -> List[Task]:
    data = run(["task", "+get-my-tasks", "--as", identity, "--complete=true", "--page-limit", "5"])
    done = [_task(i) for i in _items(data)]
    return sorted([t for t in done if t.completed_at and start <= t.completed_at < end and t.summary],
                  key=lambda t: t.completed_at)


def tasks_open(due_before: datetime, identity: str = "user") -> List[Task]:
    data = run(["task", "+get-my-tasks", "--as", identity, "--complete=false",
                "--due-end", due_before.isoformat(timespec="seconds")])
    todo = [_task(i) for i in _items(data)]
    far = datetime.max.replace(tzinfo=due_before.tzinfo)
    return sorted([t for t in todo if t.summary], key=lambda t: t.due_at or far)


def collect(start: datetime, end: datetime, cfg: Dict[str, Any], warnings: List[str]) -> LarkActivity:
    """Gather what Lark knows about the period. Each part fails independently."""
    opts = cfg.get("lark") or {}
    identity = opts.get("identity", "user")
    act = LarkActivity()
    # Plan horizon: next working day for dailies, next week for weeklies.
    horizon = end + timedelta(days=7 if (end - start).days >= 7 else 1)
    parts = [("calendar", lambda: setattr(act, "meetings", meetings(start, end, identity))),
             ("tasks", lambda: setattr(act, "tasks_done", tasks_done(start, end, identity))),
             ("tasks", lambda: setattr(act, "tasks_open", tasks_open(horizon, identity)))]
    wanted = set(opts.get("include") or ["calendar", "tasks"])
    for name, fn in parts:
        if name not in wanted:
            continue
        try:
            fn()
        except LarkError as e:
            msg = f"lark {name}: {e}"
            if msg not in warnings:
                warnings.append(msg)
    return act


# --- publishing ---------------------------------------------------------------

def _find_open_id(data: Any) -> Optional[str]:
    if isinstance(data, dict):
        v = data.get("open_id")
        if isinstance(v, str) and v.startswith("ou_"):
            return v
        data = list(data.values())
    if isinstance(data, list):
        for item in data:
            found = _find_open_id(item)
            if found:
                return found
    return None


def my_open_id() -> str:
    found = _find_open_id(run(["contact", "+search-user", "--as", "user", "--user-ids", "me"]))
    if not found:
        raise LarkError("could not look up your own open_id (lark-cli contact +search-user --user-ids me)")
    return found


def resolve_target(target: str, cfg: Dict[str, Any]) -> str:
    """Map "me" or a configured alias (e.g. "leader") to an oc_/ou_ id."""
    aliases = (cfg.get("lark") or {}).get("targets") or {}
    resolved = aliases.get(target, target)
    if resolved == "me":
        return my_open_id()
    if not resolved.startswith(("oc_", "ou_")):
        raise LarkError(f"'{target}' is not \"me\", a chat id (oc_…), a user open_id (ou_…) or an alias "
                        f"in config lark.targets")
    return resolved


def send_message(target: str, markdown: str, identity: str = "user", dry_run: bool = False) -> Any:
    flag = "--chat-id" if target.startswith("oc_") else "--user-id"
    args = ["im", "+messages-send", "--as", identity, flag, target, "--markdown", markdown]
    if dry_run:
        args.append("--dry-run")
    return run(args)


def create_doc(title: str, markdown: str, identity: str = "user", parent: Optional[str] = None) -> str:
    args = ["docs", "+create", "--as", identity, "--doc-format", "markdown", "--title", title,
            "--content", markdown]
    if parent:
        args += ["--parent-token", parent]
    data = run(args)
    doc = (data or {}).get("document") or {}
    return doc.get("url") or doc.get("document_id") or ""


def status() -> str:
    """One-line status for `report-skill doctor`."""
    if not available():
        return "not installed (optional: npx @larksuite/cli@latest install)"
    try:
        data = run(["auth", "status"], timeout=20)
    except LarkError as e:
        return f"installed, not ready: {e}"
    name = ""
    if isinstance(data, dict):
        user = data.get("user")
        name = data.get("user_name") or data.get("name") or (user.get("name", "") if isinstance(user, dict) else "")
    return f"logged in{' as ' + name if name else ''}"
