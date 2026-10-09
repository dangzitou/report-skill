"""Shared helpers for JSONL-based collectors."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterator, List


def recent_files(paths: List[Path], start: datetime) -> List[Path]:
    """Skip files that were last written before the window opened."""
    cutoff = start.timestamp()
    out = []
    for p in paths:
        try:
            if os.path.getmtime(p) >= cutoff:
                out.append(p)
        except OSError:
            continue
    return sorted(out)


def read_jsonl(path: Path) -> Iterator[dict]:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    yield obj
    except OSError:
        return
