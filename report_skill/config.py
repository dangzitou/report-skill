"""User configuration: ~/.config/report-skill/config.json (all keys optional)."""

from __future__ import annotations

import json
import locale
import os
from pathlib import Path
from typing import Any, Dict, List

DEFAULTS: Dict[str, Any] = {
    "lang": None,  # "zh" | "en"; None = the language you mostly type in
    "sources": ["claude-code", "codex", "zcode", "git", "lark"],  # lark is used only if lark-cli is installed
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
    "lark": {
        "identity": "user",  # "user" or "bot" (lark-cli --as)
        "include": ["calendar", "tasks"],  # what to read from Lark
        "targets": {},  # aliases for --to-lark, e.g. {"leader": "ou_xxx", "team": "oc_xxx"}
        "send_to": None,  # default target when --to-lark is given without a value
        "doc_folder": None,  # parent folder / wiki token for --lark-doc
    },
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
        for k, v in user.items():
            if k.startswith("_"):
                continue
            # Merge nested sections so a partial "lark" block keeps the other defaults.
            cfg[k] = {**cfg[k], **v} if isinstance(v, dict) and isinstance(cfg.get(k), dict) else v
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
    # Only overrides live here, so new defaults in later versions still apply.
    _write_user({"_doc": "All keys are optional. Change with `report-skill config set KEY VALUE`; "
                         "see https://github.com/dangzitou/report-skill#configuration"})
    return path


def _read_user() -> Dict[str, Any]:
    path = config_path()
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _write_user(data: Dict[str, Any]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def _parse(value: str) -> Any:
    try:
        return json.loads(value)
    except ValueError:
        return value  # plain strings don't need quotes


def get_value(cfg: Dict[str, Any], key: str) -> Any:
    node: Any = cfg
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def set_value(key: str, value: Any) -> None:
    """Set a dotted key in the user's config file, e.g. lark.targets.leader = ou_xxx."""
    data = _read_user()
    node = data
    parts = key.split(".")
    for part in parts[:-1]:
        if not isinstance(node.get(part), dict):
            node[part] = {}
        node = node[part]
    node[parts[-1]] = _parse(value) if isinstance(value, str) else value
    _write_user(data)


def unset_value(key: str) -> None:
    data = _read_user()
    node = data
    parts = key.split(".")
    for part in parts[:-1]:
        node = node.get(part)
        if not isinstance(node, dict):
            return
    node.pop(parts[-1], None)
    _write_user(data)
