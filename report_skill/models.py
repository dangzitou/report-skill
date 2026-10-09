"""Plain data types shared by collectors, the summarizer and renderers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple


@dataclass
class Session:
    """One chat session with a local coding agent."""

    source: str  # "claude-code" | "codex" | "zcode"
    id: str
    cwd: str
    title: str = ""
    prompts: List[Tuple[datetime, str]] = field(default_factory=list)
    files: List[Tuple[datetime, str]] = field(default_factory=list)

    def clip(self, start: datetime, end: datetime) -> Optional["Session"]:
        """Return a copy holding only the events inside [start, end), or None."""
        prompts = [(t, p) for t, p in self.prompts if start <= t < end]
        files = [(t, f) for t, f in self.files if start <= t < end]
        if not prompts and not files:
            return None
        return Session(self.source, self.id, self.cwd, self.title, prompts, files)

    @property
    def times(self) -> List[datetime]:
        return [t for t, _ in self.prompts] + [t for t, _ in self.files]


@dataclass
class Commit:
    repo: str
    sha: str
    time: datetime
    subject: str
    body: str = ""
    insertions: int = 0
    deletions: int = 0
    files_changed: int = 0
    refs: str = ""
