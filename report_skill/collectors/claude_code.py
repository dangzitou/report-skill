"""Claude Code: ~/.claude/projects/<encoded-cwd>/<session-id>.jsonl"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..models import Session
from ..util import clean_prompt, parse_iso
from ._files import read_jsonl, recent_files

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def default_root() -> Path:
    return Path.home() / ".claude" / "projects"


def _user_text(content) -> Optional[str]:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # A list containing tool_result blocks is tool output, not a human turn.
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        texts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        return "\n".join(texts) if texts else None
    return None


def parse_file(path: Path) -> Optional[Session]:
    session = Session(source="claude-code", id=path.stem, cwd="")
    for rec in read_jsonl(path):
        rtype = rec.get("type")
        if rtype in ("custom-title", "ai-title", "summary"):
            title = rec.get("customTitle") or rec.get("aiTitle") or rec.get("title") or rec.get("summary")
            # A user-set custom title wins over generated ones.
            if title and (rtype == "custom-title" or not session.title):
                session.title = str(title)
            continue
        if rtype not in ("user", "assistant") or rec.get("isSidechain"):
            continue
        if rec.get("cwd") and not session.cwd:
            session.cwd = rec["cwd"]
        ts = parse_iso(rec.get("timestamp", ""))
        if ts is None:
            continue
        msg = rec.get("message") or {}
        if rtype == "user":
            if rec.get("isMeta") or rec.get("isCompactSummary"):
                continue
            text = clean_prompt(_user_text(msg.get("content")) or "")
            if text:
                session.prompts.append((ts, text))
        else:
            for block in msg.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") in EDIT_TOOLS:
                    inp = block.get("input") or {}
                    fp = inp.get("file_path") or inp.get("notebook_path")
                    if fp:
                        session.files.append((ts, fp))
    if not session.prompts and not session.files:
        return None
    return session


def collect(start: datetime, end: datetime, root: Optional[Path] = None) -> List[Session]:
    root = Path(root) if root else default_root()
    if not root.is_dir():
        return []
    out = []
    for path in recent_files(list(root.glob("*/*.jsonl")), start):
        s = parse_file(path)
        if s:
            clipped = s.clip(start, end)
            if clipped:
                out.append(clipped)
    return out
