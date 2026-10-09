---
name: report-skill
description: Write the user's daily or weekly work report (日报 / 周报 / 月报 / standup / weekly update) from their local Claude Code, Codex and ZCode chat history, their git commits and, if lark-cli is installed, their Lark/Feishu meetings and tasks. It can also send the report on Lark/Feishu or save it as a Lark doc. Use when the user says things like "写日报", "帮我写周报", "今天干了啥", "发周报给领导", "write my standup", "weekly report", or "what did I do this week".
---

# report-skill

This skill turns what the user actually did into a report their lead can read in 30 seconds. You run one command to get the facts and a writing brief, then write the report yourself. The user should not have to do anything by hand.

## 0. Command

Use `report-skill`. If it is not on PATH, try `~/.local/bin/report-skill`. If that is missing too, run it without installing:

```bash
uvx --from git+https://github.com/dangzitou/report-skill report-skill
```

If none of these work, install it silently (see https://raw.githubusercontent.com/dangzitou/report-skill/main/INSTALL.md):

```bash
curl -fsSL https://raw.githubusercontent.com/dangzitou/report-skill/main/install.sh | sh
```

## 1. Pick the period (don't ask; infer it)

| User says | Argument |
| --- | --- |
| 日报 / today / standup (default) | `today` |
| 昨天 / yesterday | `yesterday` |
| 周报 / this week | `week` |
| 上周 / last week (also the default for 周报 on Monday morning) | `last-week` |
| a date | `YYYY-MM-DD` |
| 月报 / a range | `--since YYYY-MM-DD --until YYYY-MM-DD` |

Add `--lang zh` or `--lang en` only if the user asked for a language.

## 2. Get the brief

```bash
report-skill <period> --prompt
```

This prints the instructions, the writing guide and all collected facts as JSON. It reads local files only. Lines on stderr that start with `warning:` are non-fatal; mention them only if they explain missing data, for example that Lark is not logged in.

## 3. Write the report yourself

Follow the brief exactly. Do not call another AI CLI. The rules that matter most:
- Lead with a one-sentence conclusion. Report outcomes, not activity. Use numbers only from DATA.
- Group the work by project, most important first, and merge small items.
- Leave out anything a manager shouldn't see, such as job hunting, interviews or personal matters.
- Where a fact is missing, write `[待确认]` / `[to confirm]` instead of inventing one.

Show the finished report. Underneath it, add at most one short line listing the placeholders the user may want to fill in. If the user asks for changes, edit the report directly; there is no need to re-run the command.

## 4. Deliver (only if the user asked)

Save the final text to a file first, for example `report.md` in a temporary folder. Then:

| Request | Command |
| --- | --- |
| "save it" | write the file where the user wants it |
| "发给我自己 / send it to me" | `report-skill send report.md --to-lark me --json` |
| "发给 <someone> / post to <group>" | `report-skill send report.md --to-lark <alias or ou_/oc_ id> --yes --json` |
| "存成飞书文档 / make it a Lark doc" | `report-skill send report.md --lark-doc --json` |

**Sending to other people:** if the user's request already names the recipient and asks you to send ("把周报发给老板"), that is the approval, so pass `--yes`. If it does not, ask once in a single line ("发给 leader（ou_xxx）？") and add `--yes` after they say yes.

To find ids, check the config first with `report-skill config get lark.targets`. Otherwise look them up with `lark-cli contact +search-user --query <name>` or `lark-cli im +chat-search --query <group>`, and offer to save the result with `report-skill config set lark.targets.<alias> <id>`.

`send --json` returns a result object. Its exit codes are:
- `0`: ok.
- `1`: error. Read the `error` field; `fix` gives the command that repairs it.
- `3`: needs the user's approval. Ask, then re-run with `--yes`.

## 5. Settings (never ask the user to edit JSON)

```bash
report-skill config set lang zh
report-skill config set lark.send_to leader
report-skill config set exclude '["*/personal/*"]'
report-skill doctor --json        # what sources are visible
```

## Notes

- All reading is local and read-only. The only network calls go through `lark-cli`, and only when Lark is installed or the user asked to send.
- If Lark is not set up but the user wants it, follow section 3 of INSTALL.md. The only human step is approving a browser login.
- The writing guide is in `references/guide.zh.md` and `references/guide.en.md`. Read it when the user asks why the report is written a certain way, or wants help with the tone of a report they are sending to their manager.
