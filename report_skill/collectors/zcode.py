"""ZCode: ~/.zcode/cli/db/db.sqlite (session / message / part tables)."""

from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..models import Session
from ..util import clean_prompt, from_millis

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def default_root() -> Path:
    return Path.home() / ".zcode"


def _connect(db: Path):
    """Open read-only; fall back to a temp copy when the live DB is locked."""
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        conn.execute("select 1 from session limit 1")
        return conn, None
    except sqlite3.Error:
        tmp = tempfile.mkdtemp(prefix="report-skill-")
        for suffix in ("", "-wal", "-shm"):
            src = Path(str(db) + suffix)
            if src.exists():
                shutil.copy2(src, Path(tmp) / (db.name + suffix))
        return sqlite3.connect(str(Path(tmp) / db.name)), tmp


def _loads(raw) -> dict:
    try:
        v = json.loads(raw)
        return v if isinstance(v, dict) else {}
    except (TypeError, ValueError):
        return {}


def collect(start: datetime, end: datetime, root: Optional[Path] = None) -> List[Session]:
    root = Path(root) if root else default_root()
    db = root / "cli" / "db" / "db.sqlite"
    if not db.exists():
        return []
    lo, hi = int(start.timestamp() * 1000), int(end.timestamp() * 1000)
    conn, tmp = _connect(db)
    try:
        sessions: Dict[str, Session] = {}
        for sid, cwd, title in conn.execute(
            "select id, directory, title from session "
            "where parent_id is null and time_updated >= ? and time_created < ?",
            (lo, hi),
        ):
            sessions[sid] = Session(source="zcode", id=sid, cwd=cwd or "", title=title or "")
        if not sessions:
            return []
        marks = ",".join("?" * len(sessions))
        ids = list(sessions)

        # Human prompts: user-role messages whose semantics say a real person typed them.
        rows = conn.execute(
            f"select m.session_id, m.time_created, m.data, p.data from message m "
            f"join part p on p.message_id = m.id "
            f"where m.session_id in ({marks}) and m.time_created >= ? and m.time_created < ? "
            f"order by m.time_created, p.id",
            (*ids, lo, hi),
        )
        for sid, t, mraw, praw in rows:
            m = _loads(mraw)
            if m.get("role") != "user":
                continue
            kind = (m.get("semantics") or {}).get("kind")
            if kind not in (None, "user_prompt"):
                continue
            p = _loads(praw)
            if p.get("type") != "text" or p.get("synthetic"):
                continue
            text = clean_prompt(p.get("text", ""))
            ts = from_millis(t)
            if text and ts:
                sessions[sid].prompts.append((ts, text))

        rows = conn.execute(
            f"select session_id, time_created, data from part "
            f"where session_id in ({marks}) and time_created >= ? and time_created < ? "
            f"and data like '%\"tool\"%'",
            (*ids, lo, hi),
        )
        for sid, t, praw in rows:
            p = _loads(praw)
            if p.get("tool") not in EDIT_TOOLS:
                continue
            inp = (p.get("state") or {}).get("input") or {}
            fp = inp.get("file_path") or inp.get("filePath") or inp.get("path")
            ts = from_millis(t)
            if fp and ts:
                sessions[sid].files.append((ts, fp))
    except sqlite3.Error:
        return []
    finally:
        conn.close()
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    return [s for s in sessions.values() if s.prompts or s.files]
