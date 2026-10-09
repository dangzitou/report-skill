<div align="center">

# report-skill

**Stop reconstructing your week from memory.**
One command turns your local Claude Code / Codex / ZCode chats and git commits into a daily or weekly report your lead can read in 30 seconds.

**English** · [简体中文](README.zh.md)

[![CI](https://github.com/dangzitou/report-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/dangzitou/report-skill/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

It's Friday, 5:50 pm. You open a blank doc and wonder: **what did I actually do this week?**

Monday is already a blur, so you dig through chats, commits and notes. Thursday ends up taking half the page, Tuesday goes missing, and your lead replies "what's the headline here?"

Your AI agents already remember everything: every "fix this bug for me", every file touched, every commit. **report-skill reads those local records and writes them up the way strong reporters do.** It leads with the conclusion, reports outcomes rather than activity, pairs every problem with options, and gives every plan a deadline.

```bash
report-skill          # today's daily report
report-skill week     # this week's weekly report
```

## What you get

<table>
<tr><th>What it reads (your raw trail)</th><th>What it writes</th></tr>
<tr><td>

```text
[Claude Code] order export endpoint times out, take a look
[Claude Code] add pagination and tests
[Codex]       script to backfill region on legacy orders
[ZCode]       load-test the export endpoint
[ZCode]       polish my resume, 2nd paragraph  ← not for your boss
[git] fix(export): paginate order export (#212)
      +184 −37
[git] chore: backfill region for legacy orders
```

</td><td>

```markdown
# Daily Report · 2026-10-08 Thu
**TL;DR**: Fixed the order-export timeout with
tests; legacy-order region backfill is done. ~6h.

## Done today
1. [Order export] Switched to paginated export,
   fixing timeouts for large accounts; unit
   tests added (#212, +184/−37)
2. [Data fix] Region backfill script for legacy
   orders done, [to confirm: rows updated]

## Risks / support needed
- Load test pending, [fill in: need DBA help?]

## Tomorrow
1. Load-test report for export, by Fri noon
```

</td></tr>
</table>

> Example with made-up data. Note that the resume chat was left out, and every number missing from the source data is marked `[to confirm]` instead of invented.

## Quick start

```bash
# install (pick one; zero dependencies, Python 3.9+)
uv tool install git+https://github.com/dangzitou/report-skill
pipx install git+https://github.com/dangzitou/report-skill

# or just try it
uvx --from git+https://github.com/dangzitou/report-skill report-skill
```

No configuration needed. It finds your agent history, uses your global git identity to pick out your own commits, and hands the facts to whichever of `claude` or `codex` you already have installed. If neither is installed, it prints a clean offline draft.

```bash
report-skill                 # today (work before 4 am counts as the previous day)
report-skill yesterday
report-skill week            # this week
report-skill last-week
report-skill 2026-10-01      # a specific day
report-skill --since 2026-09-01 --until 2026-09-30   # monthly / any range

report-skill week -c         # copy to clipboard
report-skill --raw           # no AI, instant offline draft
report-skill --lang zh       # force a language (default: whatever you mostly type in)
report-skill doctor          # which sources were found
```

## Use it inside your agent: just say "write my standup"

```bash
report-skill install-skill
```

This installs the skill into `~/.claude/skills`, `~/.codex/skills` and `~/.zcode/skills`, for whichever of those agents you have. Then, in Claude Code, Codex or ZCode, ask:

> write today's standup / weekly report for last week, more formal / 帮我写周报

The agent runs `report-skill`, gets the facts plus the writing brief, writes the report in the conversation, and you can keep editing it with the agent from there.

## Sources

| Source | Location | What is read |
| --- | --- | --- |
| Claude Code | `~/.claude/projects/*/*.jsonl` | your prompts, session titles, edited files |
| Codex (CLI / Desktop) | `~/.codex/sessions/**/rollout-*.jsonl` | your prompts, thread names, files from `apply_patch` |
| ZCode | `~/.zcode/cli/db/db.sqlite` | your prompts, task titles, edited files |
| git | repos those sessions touched, plus any you configure | **your** commits and line counts (worktrees are merged) |

Everything is read **read-only**. Agent-injected noise (system reminders, `AGENTS.md`, tool output) is filtered out, so only what you actually typed is kept.

## Why the reports read well

We read 20+ highly-saved posts on Xiaohongshu (RedNote) by big-tech PMs, engineering leads and interns who earned return offers, and distilled them, along with the Pyramid Principle, PREP and SCQA, into a [writing guide](report_skill/skill/references/guide.en.md) that the AI must follow every time. The core ideas:

- **Your lead has 30 seconds.** They want progress, problems and plan, so the first line is a one-sentence summary.
- **A daily covers facts, a weekly covers change, a monthly covers meaning.** A weekly is not five dailies glued together.
- **Report outcomes, not activity.** Write "shipped OTP login, self-tested", not "worked on login".
- **Express numbers in time and money** wherever the data honestly allows.
- **Report what you prevented.** "Zero incidents after the migration" lands better than "handled 12 tickets".
- **Turn problems into multiple choice:** symptom → cause → two options plus your pick → the ask.
- **Make plans checkable:** 1–3 items, each with a deliverable and a date. "Keep pushing X" is not a plan.
- **Communication is visibility.** Good work nobody sees doesn't get counted.

On top of that, the AI must follow four red lines:
- **Never invent.** Missing facts become `[to confirm]`.
- **Never inflate.** A config tweak is not "optimized system performance".
- **Skip what your boss shouldn't see**, such as job hunting or personal matters.
- **Redact secrets.** Tokens and keys are masked before the AI ever sees them.

## Privacy

- Nothing leaves your machine by default.
- Only the AI-writing step sends a condensed summary to the `claude` or `codex` CLI **you already use**, under your existing account and config. `--raw` keeps everything fully offline.
- Anything that looks like an API key, token, password or private key is masked before it reaches a report or a prompt.
- Codex runs with `--ephemeral`, so writing the report adds no session to your history. Claude runs carry a marker, and report-skill skips those sessions next time.

## Configuration (optional)

`report-skill init` creates `~/.config/report-skill/config.json`:

```jsonc
{
  "lang": "en",                         // default: the language you mostly type in
  "ai": "claude",                       // claude | codex; default: first one installed
  "ai_model": "sonnet",                 // passed to the CLI
  "authors": ["me@company.com"],        // git authors; default: global user.email / user.name
  "scan_roots": ["~/work"],             // also scan these folders for repos
  "repos": ["~/work/infra"],            // always include these repos
  "exclude": ["*/playground/*"],        // keep these projects out of reports
  "aliases": {"/Users/me/work/svc-ord": "Order service"},
  "day_start_hour": 4,
  "sources": ["claude-code", "codex", "zcode", "git"],
  "author_name": "Sam",
  "audience": "my team lead"
}
```

To use any other model, set `"ai_command": ["ollama", "run", "qwen3"]`. The prompt is piped in on stdin.

## FAQ

**Will it tell my boss I spent three hours on my resume?**
No. The AI is told to leave out job hunting, interviews and personal matters. You can also use `exclude` to keep a whole folder out.

**How is "time spent" estimated?**
It measures the gaps between your activity (prompts, edits, commits) and treats a gap of more than 30 minutes as a break. It is an estimate, so the report only ever says "about X hours".

**I run several sessions in parallel. Is time double-counted?**
Not in the total, which uses a single merged timeline. Each project's time is computed separately, so the per-project times can add up to more than the total.

**I use Cursor / Gemini CLI / OpenCode / …**
[Open an issue](https://github.com/dangzitou/report-skill/issues/new?template=new_source.md) or send a PR. A collector is about 80 lines; see [`claude_code.py`](report_skill/collectors/claude_code.py).

**Can I send the report as-is?**
Spend a minute on it first and fill in the `[to confirm]` spots. The AI organizes the facts; you confirm them.

## Contributing

```bash
git clone https://github.com/dangzitou/report-skill && cd report-skill
python3 -m unittest discover -s tests -t .
python3 -m report_skill --raw
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
