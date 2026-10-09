---
name: report-skill
description: Write the user's daily or weekly work report (日报 / 周报 / standup / weekly update) from their local Claude Code, Codex and ZCode chat history plus their git commits. Use when the user asks things like "写日报", "帮我写周报", "今天干了啥", "write my standup", "weekly report", or "what did I do this week".
---

# report-skill

Turns what the user actually did (their AI-agent chats and git commits on this machine) into a report their lead can read in 30 seconds.

## Steps

1. **Pick the period** from the request: `today` (default), `yesterday`, `week`, `last-week`, or a date `YYYY-MM-DD`. For a custom range use `--since YYYY-MM-DD [--until YYYY-MM-DD]`.

2. **Get the facts and writing brief** with one command. It prints the instructions, the writing guide and the collected data as JSON:

   ```bash
   report-skill <period> --prompt
   ```

   If `report-skill` is not on PATH, use one of these instead:
   - `uvx --from git+https://github.com/dangzitou/report-skill report-skill <period> --prompt`
   - `python3 -m report_skill <period> --prompt` (from a clone of the repo)

   Add `--lang zh` or `--lang en` if the user asked for a language; otherwise it follows the language the user mostly types in.

3. **Write the report yourself** by following that output exactly. It is the full brief. Do not call another AI CLI. The rules that matter most:
   - Lead with the conclusion. Report outcomes, not activity. Use numbers only from DATA.
   - Leave out anything a manager shouldn't see, such as job hunting or personal matters.
   - Where a fact is missing, write `[待确认]` / `[to confirm]` instead of inventing one.

4. **Show the report**, then briefly list the placeholders the user should fill in (risks, plan, impact numbers). Offer to save it (`-o file.md` style) or to change the tone or length.

## Notes

- Everything is read locally and read-only. Nothing is uploaded except what you, the agent, already see.
- `report-skill doctor` shows which sources were found. If a source is missing, `report-skill init` creates `~/.config/report-skill/config.json`, where the user can add repos, aliases and excludes.
- The writing guide lives in `references/guide.zh.md` and `references/guide.en.md`. Read it when the user asks *why* the report is written a certain way, or wants help with the tone of a report they are sending to their manager.
