# Installing report-skill (instructions for AI agents)

> You are a coding agent (Claude Code, Codex, ZCode, OpenCode, Cursor, …). The user asked you to install **report-skill**, which writes their daily and weekly work reports from local agent chats, git history and, optionally, Lark/Feishu.
> Follow these steps in order without asking the user anything, except where a step says **ask**. 用户让你安装 report-skill：照下面的步骤做，标了 **ask** 的地方才需要问用户。

## 1. Install (one command)

macOS / Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/dangzitou/report-skill/main/install.sh | sh
```

The last line of output is either `REPORT_SKILL_OK <path-to-binary>` or `REPORT_SKILL_FAIL <reason>`.

- **OK:** continue to step 2. If `report-skill` is not on PATH in your shell, call it by the printed path for the rest of the session.
- **FAIL, or Windows, or piping to `sh` is not allowed:** run the first of these that works, then `report-skill setup`:
  ```bash
  uv tool install --force "report-skill @ git+https://github.com/dangzitou/report-skill"
  pipx install --force git+https://github.com/dangzitou/report-skill
  python3 -m pip install --user git+https://github.com/dangzitou/report-skill
  ```
- **No network installs at all:** `uvx --from git+https://github.com/dangzitou/report-skill report-skill setup` also works, and the skill falls back to `uvx` automatically.

Requirements are Python 3.9+ and git. There are no other dependencies.

## 2. Verify

```bash
report-skill doctor --json
```

Check that `this_week` shows a number greater than 0 for at least one source. If everything is 0 or `nothing found`, that is fine for a new machine; just tell the user.

`report-skill setup` has already copied the skill into every agent folder it found (`~/.claude/skills`, `~/.codex/skills`, `~/.zcode/skills`, `~/.config/opencode/skills`, `~/.agents/skills`). If your agent loads skills from somewhere else, run:

```bash
report-skill setup --skills-dir <your-skills-folder>
```

You can pick up the new skill in this session by reading `<skills-folder>/report-skill/SKILL.md` now.

## 3. Optional: Lark / Feishu

Do this only if the user uses Lark/Feishu or mentioned it.

1. Install the CLI: `npx @larksuite/cli@latest install`.
2. Run `lark-cli config init --new` in the background. It prints an authorization URL and exits by itself once the user finishes in the browser. **ask:** send the URL to the user. Then do the same with `lark-cli auth login --domain calendar,task,im,docs`. These two browser approvals are the only steps a person must do.
3. Verify with `report-skill doctor --json`. The `lark_cli` field should start with `logged in`.
4. If the user wants a default recipient, look up the id, for example with `lark-cli contact +search-user --query <name>` or `lark-cli im +chat-search --query <group>`. Then save it:
   ```bash
   report-skill config set lark.targets.leader ou_xxx
   report-skill config set lark.send_to leader
   ```

## 4. Optional settings (no file editing needed)

```bash
report-skill config set lang zh                     # or en; default: the language the user mostly types in
report-skill config set authors '["me@company.com"]'  # git identities, if not the global one
report-skill config set exclude '["*/personal/*"]'  # keep folders out of reports
report-skill config show
```

## 5. Tell the user it's ready

Reply with one short message, for example:

> report-skill 装好了 ✅ 以后直接跟我说「写今天的日报」或「写上周的周报」就行。
> report-skill is installed ✅ Just ask me "write today's standup" or "write last week's report".

Mention which sources were found and whether Lark is connected. Don't paste raw JSON.

## Uninstall

```bash
uv tool uninstall report-skill || pipx uninstall report-skill || rm -rf ~/.local/share/report-skill ~/.local/bin/report-skill
rm -rf ~/.claude/skills/report-skill ~/.codex/skills/report-skill ~/.zcode/skills/report-skill ~/.agents/skills/report-skill
rm -rf ~/.config/report-skill
```
