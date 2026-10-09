"""report-skill command line.

    report-skill                 today's daily report
    report-skill yesterday       yesterday's
    report-skill week            this week's weekly report
    report-skill last-week       last week's
    report-skill 2026-10-01      a specific day

    report-skill setup           install the agent skill + config (idempotent, no prompts)
    report-skill doctor          what was found
    report-skill send FILE       publish a finished report to Lark/Feishu
    report-skill config ...      read / change settings without editing JSON

Agent-friendly: never prompts when stdin is not a TTY, and every helper command
takes --json. Exit codes: 0 ok, 1 error, 2 bad usage, 3 needs the user's OK
(re-run with --yes once they have agreed).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import __version__, ai, config, lark, periods, summarize
from .render import draft

WEEK_WORDS = {"week": "this", "w": "this", "this-week": "this", "本周": "this",
              "last-week": "last", "lw": "last", "上周": "last"}
DAY_WORDS = {"today": "today", "d": "today", "今天": "today", "yesterday": "yesterday", "y": "yesterday",
             "昨天": "yesterday"}
# Agent home -> its skills folder. A folder is used only if the agent's home exists.
AGENT_SKILL_DIRS = {
    "Claude Code": ("~/.claude", "skills"),
    "Codex": ("~/.codex", "skills"),
    "ZCode": ("~/.zcode", "skills"),
    "OpenCode": ("~/.config/opencode", "skills"),
    "Agent Skills (shared)": ("~/.agents", "skills"),
}
EXIT_OK, EXIT_ERR, EXIT_USAGE, EXIT_NEEDS_OK = 0, 1, 2, 3
SUBCOMMANDS = ("setup", "doctor", "send", "config", "init", "install-skill", "skill")


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def _emit(result: Dict[str, Any], as_json: bool, human: List[str]) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("\n".join(human))


def in_agent() -> bool:
    """True when we are being run by a coding agent rather than typed by a person."""
    return any(k.startswith(("CLAUDECODE", "CLAUDE_CODE_", "CODEX_", "ZCODE")) for k in os.environ)


# --- setup / skill install ------------------------------------------------------

def install_skill(extra_dirs: Optional[List[str]] = None) -> List[Dict[str, str]]:
    """Copy the bundled skill into every agent found on this machine. Always refreshes."""
    src = Path(__file__).parent / "skill"
    targets = []
    for agent, (home, sub) in AGENT_SKILL_DIRS.items():
        base = Path(home).expanduser()
        if base.is_dir():
            targets.append((agent, base / sub / "report-skill"))
    for d in extra_dirs or []:
        targets.append(("custom", Path(d).expanduser() / "report-skill"))
    done = []
    for agent, dest in targets:
        try:
            if dest.exists() or dest.is_symlink():
                shutil.rmtree(dest) if dest.is_dir() and not dest.is_symlink() else dest.unlink()
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__"))
            done.append({"agent": agent, "path": str(dest), "status": "installed"})
        except OSError as e:
            done.append({"agent": agent, "path": str(dest), "status": f"failed: {e}"})
    return done


def status_info(cfg: Dict[str, Any], scan: bool = True) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "version": __version__,
        "command": shutil.which("report-skill") or "",
        "config": str(config.config_path()),
        "config_exists": config.config_path().exists(),
        "lang": cfg.get("lang") or "auto",
        "ai_writer": ai.detect(cfg.get("ai")) or None,
        "lark_cli": lark.status() if lark.available() else "not installed",
    }
    if scan:
        r = summarize.build(periods.weekly("this", int(cfg.get("day_start_hour", 4))), cfg)
        info["this_week"] = {name: (r.sources.get(name, 0) if name in cfg["sources"] else "disabled")
                             for name in ["claude-code", "codex", "zcode", "git", "lark"]}
        if info["this_week"]["lark"] != "disabled" and not lark.available():
            info["this_week"]["lark"] = "lark-cli not installed"
        info["warnings"] = r.warnings
    return info


def cmd_setup(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(prog="report-skill setup",
                                 description="Install the agent skill and a default config. Safe to re-run.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--lang", choices=["zh", "en"], help="pin the report language")
    ap.add_argument("--skills-dir", action="append", metavar="DIR", help="also install into this skills folder")
    args = ap.parse_args(argv)
    skills = install_skill(args.skills_dir)
    created = False
    if not config.config_path().exists():
        config.init()
        created = True
    if args.lang:
        config.set_value("lang", args.lang)
    info = status_info(config.load())
    info.update({"skills": skills, "config_created": created})
    next_steps = ["Ask your agent: 写今天的日报 / write my standup"]
    if not skills:
        next_steps.insert(0, "No agent skills folder found; re-run with --skills-dir <your agent's skills folder>")
    if not info["ai_writer"]:
        next_steps.append("Optional: install Claude Code or Codex CLI so `report-skill` can polish reports by itself")
    if info["lark_cli"] == "not installed":
        next_steps.append("Optional (Lark/Feishu): npx @larksuite/cli@latest install && "
                          "lark-cli auth login --domain calendar,task,im,docs")
    info["next_steps"] = next_steps
    human = [f"report-skill {__version__} is set up."]
    human += [f"  {'✓' if s['status'] == 'installed' else '✗'} {s['agent']}: {s['path']} ({s['status']})"
              for s in skills] or ["  ! no agent folders found; pass --skills-dir DIR"]
    human.append(f"  config: {info['config']}{' (created)' if created else ''}")
    human.append(f"  AI writer: {info['ai_writer'] or 'none (offline drafts; agents write the report themselves)'}")
    human.append(f"  lark-cli: {info['lark_cli']}")
    human.append("  this week: " + ", ".join(f"{k} {v}" for k, v in info["this_week"].items()))
    human += ["next:"] + [f"  - {s}" for s in next_steps]
    _emit(info, args.json, human)
    failed = [s for s in skills if s["status"] != "installed"]
    return EXIT_ERR if failed else EXIT_OK


def cmd_doctor(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(prog="report-skill doctor", description="Show what report-skill can see.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    info = status_info(config.load())
    human = [f"report-skill {info['version']}  ·  config: {info['config']}"
             f"{'' if info['config_exists'] else ' (not created, using defaults)'}",
             f"language: {info['lang']}   AI writer: {info['ai_writer'] or 'none found (offline drafts only)'}",
             f"lark-cli: {info['lark_cli']}",
             "this week:"]
    human += [f"  {k:<12} {v if isinstance(v, str) else (f'{v} found' if v else 'nothing found')}"
              for k, v in info["this_week"].items()]
    human += [f"  ! {w}" for w in info["warnings"]]
    _emit(info, args.json, human)
    return EXIT_OK


def cmd_config(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(
        prog="report-skill config",
        description="Read or change settings. KEY uses dots for nesting, e.g. lark.targets.leader. "
                    "VALUE is parsed as JSON when possible, so [\"a\",\"b\"], true and 4 work.")
    ap.add_argument("action", choices=["show", "path", "get", "set", "unset"])
    ap.add_argument("key", nargs="?")
    ap.add_argument("value", nargs="?")
    args = ap.parse_args(argv)
    if args.action == "path":
        print(config.config_path())
    elif args.action == "show":
        print(json.dumps(config.load(), ensure_ascii=False, indent=2))
    elif not args.key:
        ap.error("KEY is required")
    elif args.action == "get":
        value = config.get_value(config.load(), args.key)
        print(json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value)
    elif args.action == "set":
        if args.value is None:
            ap.error("VALUE is required")
        config.set_value(args.key, args.value)
        _err(f"set {args.key}")
    else:
        config.unset_value(args.key)
        _err(f"unset {args.key}")
    return EXIT_OK


# --- publishing ------------------------------------------------------------------

def _confirm(question: str) -> bool:
    if not sys.stdin.isatty():
        return False
    _err(question + " [y/N] ")
    try:
        return input().strip().lower() in ("y", "yes")
    except EOFError:
        return False


def publish_lark(text: str, cfg: Dict[str, Any], lang: str, to_lark: Optional[str], lark_doc: bool,
                 yes: bool, dry_run: bool) -> Dict[str, Any]:
    """Send and/or save to Lark. Returns a result dict with an `exit` code."""
    opts = cfg.get("lark") or {}
    identity = opts.get("identity", "user")
    result: Dict[str, Any] = {"exit": EXIT_OK}
    if not lark.available():
        result.update(exit=EXIT_ERR, error="lark-cli not found",
                      fix="npx @larksuite/cli@latest install && lark-cli auth login --domain calendar,task,im,docs")
        return result
    if lark_doc:
        title = text.lstrip("# ").splitlines()[0].strip() if text.strip() else "Report"
        try:
            result["doc_url"] = lark.create_doc(title, text, identity, opts.get("doc_folder"))
        except lark.LarkError as e:
            result.update(exit=EXIT_ERR, doc_error=str(e))
    if to_lark is not None:
        name = to_lark or opts.get("send_to") or ""
        try:
            target = lark.resolve_target(name, cfg)
        except lark.LarkError as e:
            result.update(exit=EXIT_ERR, error=str(e))
            return result
        result["target"] = {"name": name, "id": target}
        # A message to someone else is seen by other people: it needs an explicit yes,
        # either typed here or passed as --yes by an agent after the user agreed in chat.
        if not (name == "me" or dry_run or yes or _confirm(
                f"{'发送到飞书' if lang == 'zh' else 'Send to Lark'} {name} (as {identity})?")):
            result.update(exit=EXIT_NEEDS_OK, sent=False,
                          hint=f"Ask the user to approve sending to '{name}', then re-run with --yes.")
            return result
        try:
            lark.send_message(target, text, identity, dry_run=dry_run)
            result["sent"] = not dry_run
            result["dry_run"] = dry_run
        except lark.LarkError as e:
            result.update(exit=EXIT_ERR, sent=False, error=str(e))
    return result


def _report_publish(result: Dict[str, Any], lang: str) -> None:
    if result.get("doc_url"):
        _err(f"{'已保存为飞书文档' if lang == 'zh' else 'saved as Lark doc'}: {result['doc_url']}")
    if result.get("sent"):
        _err(("已发送到飞书 " if lang == "zh" else "sent to Lark ") + result["target"]["name"])
    if result.get("dry_run"):
        _err("dry run ok, nothing sent")
    for key in ("error", "doc_error"):
        if result.get(key):
            _err(f"error: {result[key]}" + (f"\n  fix: {result['fix']}" if result.get("fix") else ""))
    if result.get("exit") == EXIT_NEEDS_OK:
        _err(f"not sent: {result['hint']}")


def cmd_send(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(prog="report-skill send",
                                 description="Publish a finished Markdown report (e.g. one your agent wrote).")
    ap.add_argument("file", nargs="?", default="-", help="Markdown file, or - for stdin (default)")
    ap.add_argument("--to-lark", nargs="?", const="", metavar="TARGET",
                    help="me | oc_ chat id | ou_ open_id | alias from lark.targets (default: lark.send_to)")
    ap.add_argument("--lark-doc", action="store_true", help="save as a Lark/Feishu doc")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("-y", "--yes", action="store_true", help="the user has approved sending")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.to_lark is None and not args.lark_doc:
        ap.error("nothing to do: pass --to-lark [TARGET] and/or --lark-doc")
    text = sys.stdin.read() if args.file == "-" else Path(args.file).expanduser().read_text(encoding="utf-8")
    if not text.strip():
        ap.error("the report is empty")
    cfg = config.load()
    lang = cfg.get("lang") or config.guess_lang([text])
    result = publish_lark(text, cfg, lang, args.to_lark, args.lark_doc, args.yes, args.dry_run)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _report_publish(result, lang)
    return result["exit"]


# --- the report itself ---------------------------------------------------------------

def _period(args, cfg):
    hour = int(cfg.get("day_start_hour", 4))
    if args.since:
        return periods.custom(args.since, args.until, hour)
    when = (args.when or "today").lower()
    if when in WEEK_WORDS:
        return periods.weekly(WEEK_WORDS[when], hour)
    return periods.daily(DAY_WORDS.get(when, when), hour)


def _copy(text: str) -> bool:
    for cmd in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"], ["clip"]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd, input=text, text=True)
            return True
    return False


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in SUBCOMMANDS:
        cmd, rest = argv[0], argv[1:]
        if cmd in ("install-skill", "skill", "init"):
            cmd = "setup"
        return {"setup": cmd_setup, "doctor": cmd_doctor, "send": cmd_send, "config": cmd_config}[cmd](rest)

    ap = argparse.ArgumentParser(
        prog="report-skill",
        description="Write your daily / weekly report from local AI-agent chats, git history and Lark.",
        epilog="more: report-skill setup | doctor | send FILE | config  (each takes --help)",
    )
    ap.add_argument("when", nargs="?", default="today",
                    help="today (default) | yesterday | week | last-week | YYYY-MM-DD | -N days")
    ap.add_argument("--raw", action="store_true", help="skip the AI step and print the offline draft")
    ap.add_argument("--ai", metavar="NAME", help="AI writer: claude | codex (default: first one installed)")
    ap.add_argument("-m", "--model", help="model for the AI writer, e.g. sonnet or gpt-5.5")
    ap.add_argument("--json", action="store_true", help="print the collected facts as JSON")
    ap.add_argument("--prompt", action="store_true",
                    help="print the full writing brief (instructions + guide + facts) for an agent to follow")
    ap.add_argument("--lang", choices=["zh", "en"], help="report language (default: the language you mostly type in)")
    ap.add_argument("--since", metavar="DATE", help="custom range start (YYYY-MM-DD)")
    ap.add_argument("--until", metavar="DATE", help="custom range end, inclusive (default: today)")
    ap.add_argument("--only", metavar="SRC", help="comma-separated sources: claude-code,codex,zcode,git,lark")
    ap.add_argument("-o", "--output", metavar="FILE", help="also write the report to FILE")
    ap.add_argument("-c", "--copy", action="store_true", help="copy the report to the clipboard")
    ap.add_argument("--to-lark", nargs="?", const="", metavar="TARGET",
                    help="send on Lark/Feishu: me | oc_ chat id | ou_ open_id | alias from lark.targets")
    ap.add_argument("--lark-doc", action="store_true", help="save the report as a Lark/Feishu doc")
    ap.add_argument("--dry-run", action="store_true", help="with --to-lark: preview the request, send nothing")
    ap.add_argument("-y", "--yes", action="store_true", help="the user has approved sending to Lark")
    ap.add_argument("-V", "--version", action="version", version=f"report-skill {__version__}")
    args = ap.parse_args(argv)

    cfg = config.load()
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
        return EXIT_OK
    if args.prompt:
        print(ai.build_prompt(report, lang, cfg))
        return EXIT_OK

    text = draft(report, lang)
    if not args.raw and (report.projects or report.lark):
        engine = ai.detect(args.ai or cfg.get("ai"))
        if in_agent() and not (args.ai or cfg.get("ai")):
            _err("note: running inside an agent; use `--prompt` and let the agent write the report itself "
                 "(faster, and it can keep editing). Falling back to the offline draft.")
        elif engine or cfg.get("ai_command"):
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
    if args.to_lark is not None or args.lark_doc:
        result = publish_lark(text, cfg, lang, args.to_lark, args.lark_doc, args.yes, args.dry_run)
        _report_publish(result, lang)
        return result["exit"]
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
