# Changelog

## 0.3.0 — 2026-10-09

Agent-first install and operation.

- **Install by message**: tell any agent `Install report-skill for me: https://raw.githubusercontent.com/dangzitou/report-skill/main/INSTALL.md`. INSTALL.md is a step-by-step runbook for agents.
- `install.sh` one-liner: uv → pipx → private venv fallback, then `report-skill setup`; ends with `REPORT_SKILL_OK <path>` / `REPORT_SKILL_FAIL <reason>`.
- `report-skill setup [--json] [--skills-dir DIR]`: idempotent; installs the skill into Claude Code, Codex, ZCode, OpenCode and `~/.agents`; writes a minimal config.
- `report-skill send FILE|- --to-lark … --lark-doc --yes --json`: publish a report the agent wrote.
- `report-skill config show|path|get|set|unset` with dotted keys and JSON values.
- `doctor --json`; documented exit codes (3 = needs the user's OK, re-run with `--yes`).
- Never prompts without a TTY; inside an agent, `report-skill` points to `--prompt` instead of spawning a nested AI CLI.
- SKILL.md rewritten as an autonomous workflow (period inference, delivery, approval rules, self-repair).
- `init` / `install-skill` are now aliases of `setup`.

## 0.2.0 — 2026-10-09

- **Lark / Feishu adapter** via the official [lark-cli](https://github.com/larksuite/cli):
  - reads meetings (skips declined), completed tasks and tasks coming due; open tasks drive the plan section
  - `--to-lark me` sends the report to yourself as a draft
  - `--to-lark <oc_/ou_/alias>` sends the report as a message (asks for confirmation; `--yes` for scripts, `--dry-run` to preview)
  - `--lark-doc` saves the report as a Lark doc
  - `lark` config block: identity, include, targets, send_to, doc_folder
- `doctor` shows lark-cli status.
- Summary line only mentions parts that have data.

## 0.1.0 — 2026-10-09

- First release.
- Collectors: Claude Code, Codex (CLI/Desktop), ZCode, git (worktree-aware, author-filtered).
- `report-skill [today|yesterday|week|last-week|DATE]`, `--since/--until`, `--raw`, `--json`, `--prompt`, `-c`, `-o`.
- AI writer auto-detects `claude` / `codex`; offline draft fallback.
- Writing guide (zh/en) distilled from Xiaohongshu posts on reporting to your lead.
- Agent skill: `report-skill install-skill` for Claude Code, Codex and ZCode.
- Secret redaction; auto language detection; 4 am day boundary.
