"""Collectors read local agent history and git logs. Each one is read-only."""

from . import claude_code, codex, git, zcode

AGENT_COLLECTORS = {
    "claude-code": claude_code.collect,
    "codex": codex.collect,
    "zcode": zcode.collect,
}

__all__ = ["AGENT_COLLECTORS", "git"]
