"""User configuration: ~/.config/report-skill/config.json (all keys optional)."""

from __future__ import annotations

import json
import locale
import os
from pathlib import Path
from typing import Any, Dict, List

DEFAULTS: Dict[str, Any] = {
    "lang": None,  # "zh" | "en"; None = the language you mostly type in
    "sources": ["claude-code", "codex", "zcode", "git"],
    "authors": [],  # git author emails/names; empty = your global git identity
    "repos": [],  # extra repos to always include
    "scan_roots": [],  # directories to scan for repos (depth 3)
    "exclude": [],  # fnmatch patterns on project paths, e.g. "*/scratch/*"
    "aliases": {},  # {"/abs/path/to/repo": "Display name"}
    "day_start_hour": 4,  # work done before 4am counts toward the previous day
    "idle_minutes": 30,  # gap that ends a stretch of focused work
    "paths": {},  # override data dirs: {"claude-code": "...", "codex": "...", "zcode": "..."}
    "ai": None,  # "claude" | "codex"; None = first one installed
    "ai_model": None,  # e.g. "sonnet", "gpt-5.5"; None = the CLI's own default
    "ai_command": None,  # e.g. ["claude", "-p"]; the prompt is piped on stdin
    "author_name": "",
    "audience": "",  # who reads it, e.g. "my team lead"
}


def config_path() -> Path:
    env = os.environ.get("REPORT_SKILL_CONFIG")
    if env:
        return Path(env).expanduser()
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "report-skill" / "config.json"


def system_lang() -> str:
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        v = os.environ.get(var, "")
        if v:
            return "zh" if v.lower().startswith("zh") else "en"
    try:
        loc = locale.getlocale()[0] or ""
    except ValueError:
        loc = ""
    return "zh" if loc.lower().startswith("zh") else "en"


def load() -> Dict[str, Any]:
    cfg = dict(DEFAULTS)
    path = config_path()
    if path.exists():
        with open(path, encoding="utf-8") as fh:
            user = json.load(fh)
        cfg.update({k: v for k, v in user.items() if not k.startswith("_")})
    return cfg


def guess_lang(texts: List[str]) -> str:
    """Write the report in the language the user actually works in."""
    sample = "".join(texts)[:20000]
    cjk = sum(1 for ch in sample if "\u4e00" <= ch <= "\u9fff")
    latin = sum(1 for ch in sample if ch.isascii() and ch.isalpha())
    if cjk + latin < 8:
        return system_lang()
    # One Chinese character carries roughly as much as a short English word.
    return "zh" if cjk * 4 >= latin else "en"


def init(force: bool = False) -> Path:
    path = config_path()
    if path.exists() and not force:
        raise FileExistsError(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    sample = dict(DEFAULTS)
    sample["scan_roots"] = ["~/Developer", "~/code", "~/projects"]
    sample["_doc"] = "See https://github.com/dangzitou/report-skill#configuration"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(sample, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return path
