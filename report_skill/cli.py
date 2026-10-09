"""report-skill command line.

    report-skill                 today's daily report
    report-skill yesterday       yesterday's
    report-skill week            this week's weekly report
    report-skill last-week       last week's
    report-skill 2026-10-01      a specific day
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__, ai, config, periods, summarize
from .render import draft

WEEK_WORDS = {"week": "this", "w": "this", "this-week": "this", "本周": "this",
              "last-week": "last", "lw": "last", "上周": "last"}
DAY_WORDS = {"today": "today", "d": "today", "今天": "today", "yesterday": "yesterday", "y": "yesterday",
             "昨天": "yesterday"}
AGENT_SKILL_DIRS = {"Claude Code": "~/.claude", "Codex": "~/.codex", "ZCode": "~/.zcode"}


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def _period(args, cfg):
    hour = int(cfg.get("day_start_hour", 4))
    if args.since:
        return periods.custom(args.since, args.until, hour)
    when = (args.when or "today").lower()
    if when in WEEK_WORDS:
        return periods.weekly(WEEK_WORDS[when], hour)
    return periods.daily(DAY_WORDS.get(when, when), hour)


def install_skill(force: bool) -> int:
    src = Path(__file__).parent / "skill"
    done = 0
    for agent, home in AGENT_SKILL_DIRS.items():
        base = Path(home).expanduser()
        if not base.is_dir():
            continue
        dest = base / "skills" / "report-skill"
        if dest.exists() and not force:
            print(f"  · {agent}: already installed at {dest} (use --force to update)")
            continue
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__"))
        print(f"  ✓ {agent}: {dest}")
        done += 1
    if not done:
        print("  Nothing new installed. Copy `skills/report-skill/` into your agent's skills folder manually.")
    return 0


def doctor(cfg) -> int:
    p = periods.weekly("this", int(cfg.get("day_start_hour", 4)))
    r = summarize.build(p, cfg)
    print(f"report-skill {__version__}  ·  config: {config.config_path()}"
          f"{'' if config.config_path().exists() else ' (not created, using defaults)'}")
    print(f"language: {cfg.get('lang') or 'auto (from what you write)'}   AI writer: {ai.detect(cfg.get('ai')) or 'none found (offline drafts only)'}")
    print("this week:")
    for name in ["claude-code", "codex", "zcode", "git"]:
        n = r.sources.get(name)
        state = "disabled" if name not in cfg["sources"] else (f"{n} found" if n else "nothing found")
        print(f"  {name:<12} {state}")
    for w in r.warnings:
        print(f"  ! {w}")
    return 0


def _copy(text: str) -> bool:
    for cmd in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"], ["clip"]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd, input=text, text=True)
            return True
    return False


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="report-skill",
        description="Write your daily / weekly report from local AI-agent chats and git history.",
        epilog="examples: report-skill | report-skill week | report-skill last-week --raw | report-skill -1 --lang en",
    )
    ap.add_argument("when", nargs="?", default="today",
                    help="today (default) | yesterday | week | last-week | YYYY-MM-DD | -N days; "
                         "or: init | install-skill | doctor")
    ap.add_argument("--raw", action="store_true", help="skip the AI step and print the offline draft")
    ap.add_argument("--ai", metavar="NAME", help="AI writer: claude | codex (default: first one installed)")
    ap.add_argument("-m", "--model", help="model for the AI writer, e.g. sonnet or gpt-5.5")
    ap.add_argument("--json", action="store_true", help="print the collected facts as JSON (for agents)")
    ap.add_argument("--prompt", action="store_true", help="print the AI prompt instead of running it")
    ap.add_argument("--lang", choices=["zh", "en"], help="report language (default: system locale)")
    ap.add_argument("--since", metavar="DATE", help="custom range start (YYYY-MM-DD)")
    ap.add_argument("--until", metavar="DATE", help="custom range end, inclusive (default: today)")
    ap.add_argument("--only", metavar="SRC", help="comma-separated sources: claude-code,codex,zcode,git")
    ap.add_argument("-o", "--output", metavar="FILE", help="also write the report to FILE")
    ap.add_argument("-c", "--copy", action="store_true", help="copy the report to the clipboard")
    ap.add_argument("--force", action="store_true", help="overwrite for init / install-skill")
    ap.add_argument("-V", "--version", action="version", version=f"report-skill {__version__}")
    args = ap.parse_args(argv)

    if args.when == "init":
        try:
            print(f"created {config.init(args.force)}")
        except FileExistsError as e:
            print(f"{e} already exists (use --force to overwrite)")
        return 0
    if args.when in ("install-skill", "skill"):
        return install_skill(args.force)

    cfg = config.load()
    if args.when == "doctor":
        return doctor(cfg)

    try:
        period = _period(args, cfg)
    except ValueError:
        ap.error(f"don't understand '{args.when}'; try today, yesterday, week, last-week or YYYY-MM-DD")
    only = [s.strip() for s in args.only.split(",")] if args.only else None
    report = summarize.build(period, cfg, only)
    for w in report.warnings:
        _err(f"warning: {w}")
    lang = args.lang or cfg.get("lang") or config.guess_lang([t for s in report.sessions for _, t in s.prompts]
                                                             + [c.subject for c in report.commits])

    if args.json:
        print(json.dumps(summarize.to_dict(report), ensure_ascii=False, indent=2))
        return 0
    if args.prompt:
        print(ai.build_prompt(report, lang, cfg))
        return 0

    text = draft(report, lang)
    if not args.raw and report.projects:
        engine = ai.detect(args.ai or cfg.get("ai"))
        if engine or cfg.get("ai_command"):
            _err(f"✍  {'正在用' if lang == 'zh' else 'Writing with'} {engine or cfg['ai_command'][0]}"
                 f"{' 润色报告…' if lang == 'zh' else '…'}")
            try:
                text = ai.run(ai.build_prompt(report, lang, cfg), engine or "", cfg.get("ai_command"),
                              args.model or cfg.get("ai_model"))
            except ai.AIError as e:
                _err(f"warning: AI step failed ({e}); showing the offline draft instead")
        else:
            _err("tip: install Claude Code or Codex CLI for a polished report; showing the offline draft")

    sys.stdout.write(text)
    if args.output:
        Path(args.output).expanduser().write_text(text, encoding="utf-8")
        _err(f"saved to {args.output}")
    if args.copy:
        _err("copied to clipboard" if _copy(text) else "warning: no clipboard tool found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
