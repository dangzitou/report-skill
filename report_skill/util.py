"""Small helpers: timestamps, prompt cleaning and secret redaction."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

# Text that agents inject into the "user" role but the human never typed.
_NOISE_PREFIXES = (
    "<command-",
    "<local-command",
    "<environment_context",
    "<user_instructions",
    "<system-reminder",
    "<permissions",
    "<INSTRUCTIONS>",
    "<turn_aborted",
    "<subagent",
    "<task-notification",
    "<report-skill>",
    "# AGENTS.md",
    "# CLAUDE.md",
    "Caveat: The messages below",
    "[Request interrupted",
    "This session is being continued from a previous conversation",
)

_SECRET_PATTERNS = [
    re.compile(r"\b(sk|pk|rk)-[A-Za-z0-9_\-]{16,}"),  # OpenAI / Anthropic / Stripe style
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),  # GitHub tokens
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bxox[abposr]-[A-Za-z0-9\-]{10,}"),  # Slack
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS access key id
    re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}"),  # Google API key
    re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),  # JWT
    re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._\-]{16,}"),
    re.compile(
        r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key)\b(\s*[:=]\s*)(\S{4,})"
    ),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
]


def redact(text: str) -> str:
    """Mask things that look like credentials before they reach a report or an LLM."""
    for pat in _SECRET_PATTERNS:
        if pat.groups >= 3:
            text = pat.sub(lambda m: m.group(1) + m.group(2) + "***", text)
        else:
            text = pat.sub("***REDACTED***", text)
    return text


def clean_prompt(text: str, limit: int = 400) -> Optional[str]:
    """Return a one-paragraph version of a human prompt, or None if it is agent noise."""
    if not text:
        return None
    text = text.strip()
    if not text or text.startswith(_NOISE_PREFIXES):
        return None
    # Drop inline reminders some agents append to the real prompt.
    text = re.sub(r"<system-reminder>[\s\S]*?</system-reminder>", "", text).strip()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return None
    text = redact(text)
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def parse_iso(value: str) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp (with optional trailing Z) into an aware local datetime."""
    if not value:
        return None
    try:
        v = value.strip().replace("Z", "+00:00")
        # Python 3.9 fromisoformat only accepts 0/3/6 fractional digits.
        m = re.match(r"^(.*T\d\d:\d\d:\d\d)(\.\d+)?(.*)$", v)
        if m and m.group(2):
            frac = (m.group(2)[1:] + "000000")[:6]
            v = f"{m.group(1)}.{frac}{m.group(3)}"
        dt = datetime.fromisoformat(v)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone()


def from_millis(ms) -> Optional[datetime]:
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).astimezone()
    except (TypeError, ValueError, OSError, OverflowError):
        return None
