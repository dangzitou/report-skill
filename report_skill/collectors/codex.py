"""OpenAI Codex (CLI / Desktop): ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..models import Session
from ..util import clean_prompt, parse_iso
from ._files import read_jsonl, recent_files

_PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", re.M)


def default_root() -> Path:
    return Path.home() / ".codex"


def _thread_names(root: Path) -> Dict[str, str]:
    names: Dict[str, str] = {}
    for rec in read_jsonl(root / "session_index.jsonl"):
        if rec.get("id") and rec.get("thread_name"):
            names[rec["id"]] = rec["thread_name"]  # later entries are renames
    return names


def _patch_files(text: str, cwd: str) -> List[str]:
    files = []
    for f in _PATCH_FILE.findall(text or ""):
        f = f.strip()
        if cwd and not f.startswith("/"):
            f = f"{cwd.rstrip('/')}/{f}"
        files.append(f)
    return files


def parse_file(path: Path, names: Optional[Dict[str, str]] = None) -> Optional[Session]:
    session = Session(source="codex", id=path.stem, cwd="")
    event_prompts = []
    item_prompts = []
    for rec in read_jsonl(path):
        rtype = rec.get("type")
        payload = rec.get("payload") or {}
        ts = parse_iso(rec.get("timestamp", ""))
        if rtype == "session_meta":
            session.id = payload.get("id") or payload.get("session_id") or session.id
            session.cwd = payload.get("cwd") or session.cwd
            continue
        if rtype == "turn_context" and payload.get("cwd") and not session.cwd:
            session.cwd = payload["cwd"]
        if ts is None:
            continue
        ptype = payload.get("type")
        if rtype == "event_msg" and ptype == "user_message":
            text = clean_prompt(payload.get("message", ""))
            if text:
                event_prompts.append((ts, text))
        elif rtype == "response_item" and ptype == "message" and payload.get("role") == "user":
            for block in payload.get("content") or []:
                if isinstance(block, dict) and block.get("type") in ("input_text", "text"):
                    text = clean_prompt(block.get("text", ""))
                    if text:
                        item_prompts.append((ts, text))
        elif rtype == "response_item" and ptype in ("custom_tool_call", "function_call"):
            raw = payload.get("input") or payload.get("arguments") or ""
            if "*** Begin Patch" in raw:
                for f in _patch_files(raw.replace("\\n", "\n"), session.cwd):
                    session.files.append((ts, f))
    # Newer rollouts only carry response items; older ones carry both, so prefer events.
    session.prompts = event_prompts or item_prompts
    if names and session.id in names:
        session.title = names[session.id]
    if not session.prompts and not session.files:
        return None
    return session


def collect(start: datetime, end: datetime, root: Optional[Path] = None) -> List[Session]:
    root = Path(root) if root else default_root()
    if not root.is_dir():
        return []
    names = _thread_names(root)
    paths = list((root / "sessions").rglob("*.jsonl")) + list((root / "archived_sessions").glob("*.jsonl"))
    out = []
    seen = set()
    for path in recent_files(paths, start):
        s = parse_file(path, names)
        if s and s.id not in seen:
            seen.add(s.id)
            clipped = s.clip(start, end)
            if clipped:
                out.append(clipped)
    return out
