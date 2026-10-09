"""Turn collected facts into a polished report with whichever agent CLI is installed."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .render import draft
from .summarize import Report, to_dict

GUIDES = Path(__file__).parent / "skill" / "references"
MARKER = "<report-skill>"  # lets our collectors skip the sessions this call creates

# Tried in this order when the user has not picked one.
PRESETS = ["claude", "codex"]


def guide(lang: str) -> str:
    return (GUIDES / f"guide.{lang}.md").read_text(encoding="utf-8")


def compact(report: Report, max_prompts: int = 12, max_commits: int = 40) -> Dict[str, Any]:
    """Trim the raw facts so a busy week still fits comfortably in one prompt."""
    data = to_dict(report)
    for p in data["projects"]:
        p["commits"] = [{k: c[k] for k in ("time", "subject", "body", "insertions", "deletions")}
                        for c in p["commits"][:max_commits]]
        for c in p["commits"]:
            c["body"] = c["body"][:200]
        for s in p["agent_sessions"]:
            prompts = s["prompts"]
            if len(prompts) > max_prompts:  # keep how it started and how it ended
                half = max_prompts // 2
                prompts = prompts[:half] + [f"... ({len(prompts) - max_prompts} more) ..."] + prompts[-half:]
            s["prompts"] = [x[:220] for x in prompts]
            files = s.pop("files_edited")
            s["files_edited_count"] = len(files)
            s["files_edited_sample"] = files[:8]
    data.pop("warnings", None)
    return data


INSTRUCTIONS = {
    "zh": """你是我的汇报助手。请根据下方 DATA，替我写一份发给直属领导的{kind}。用中文。

严格遵守 GUIDE 里的写作规范，另外：
1. DATA 是唯一事实来源。agent_sessions.prompts 是我让 AI 做的事（代表意图），commits 是真正落地的产出（代表证据）。只有对话没有提交、结果又不明确的，写成“进行中 / 排查中 / 调研”，不要写成“完成”。
2. 站在领导视角重新组织：按项目或目标分组，重点在前。环境配置、装工具、闲聊式提问合并成一条或直接删掉。求职、简历、面试、私人事务等不该给领导看的内容一律不写。
3. 不编造。数字只能来自 DATA。某处如果需要业务影响数据但 DATA 里没有，写 `[待确认：…]`。
4. 风险只从证据推断，比如反复报错、回滚提交、明确受阻；没有就写一行 `[待补充：有无卡点 / 需要的支持]`。
5. 计划根据未完成的线索推断，每条带交付物和节点；推断不出的用 `[待确认]`。
6. 时长是按活动间隔估算的，最多写“约 X 小时”，不要精确到分钟。
7. DATA.lark 来自飞书：tasks_completed 是已完成的证据，可以直接写进成果；meetings 只挑评审、决策、对齐类的关键会议，用一句话带过，例会不必逐条列；tasks_open_due_soon 是排计划的首要依据，截止日期要保留。
8. 只输出 Markdown 正文：不要前言，不要解释，也不要用代码块包裹。
9. 篇幅：{length}。

参考结构（可按实际删减）：
{template}""",
    "en": """You are my reporting assistant. Using DATA below, write the {kind} I will send to my manager. Write in English.

Follow GUIDE strictly. Also:
1. DATA is the only source of truth. agent_sessions.prompts are what I asked AI agents to do (intent); commits are what actually shipped (evidence). If there is a conversation but no commit and the outcome is unclear, call it in progress / investigating, not done.
2. Reorganize from the manager's point of view: group by project or goal, most important first. Merge or drop environment setup, tool installs and casual Q&A. Leave out anything a manager should not see (job hunting, resumes, interviews, personal matters).
3. Never invent. Numbers must come from DATA. Where an impact number would help but is missing, write `[to confirm: …]`.
4. Risks only from evidence (repeated errors, reverts, explicit blockers); otherwise one line `[fill in: blockers / support needed]`.
5. Infer the plan from unfinished threads; each item gets a deliverable and a deadline, or `[to confirm]`.
6. Time is an estimate from activity gaps; at most say "about X hours".
7. DATA.lark comes from Lark/Feishu: tasks_completed is evidence of done work; from meetings mention only key reviews, decisions or alignments in one line (skip routine syncs); tasks_open_due_soon is the primary input for the plan, keep their due dates.
8. Output the Markdown report only: no preamble, no explanations, no code fences around it.
9. Length: {length}.

Suggested structure (trim as needed):
{template}""",
}

TEMPLATES = {
    ("zh", "daily"): "# 工作日报 · 日期 周X\n**一句话总结**：…\n## 今日完成\n1. 【项目】做成了什么（证据/数据）\n## 风险 / 需要支持\n## 明日计划\n1. …（交付物 + 节点）",
    ("zh", "weekly"): "# 工作周报 · 起止日期\n**本周概览**：…（结论先行，2–3 句）\n## 重点成果\n### 1. 项目…\n## 问题与思考\n## 下周计划\n1. …（交付物 + 节点 + 验收标准）\n## 沉淀 / 成长（可选）",
    ("en", "daily"): "# Daily Report · date\n**TL;DR**: …\n## Done today\n1. [Project] outcome (evidence/number)\n## Risks / support needed\n## Tomorrow\n1. … (deliverable + deadline)",
    ("en", "weekly"): "# Weekly Report · date range\n**Summary**: … (conclusion first, 2–3 sentences)\n## Key results\n### 1. Project …\n## Problems & thinking\n## Next week\n1. … (deliverable + deadline + done-when)\n## Leverage / growth (optional)",
}


def build_prompt(report: Report, lang: str, cfg: Dict[str, Any]) -> str:
    kind = "weekly" if report.period.kind != "daily" else "daily"
    names = {"zh": {"daily": "日报", "weekly": "周报"}, "en": {"daily": "daily report", "weekly": "weekly report"}}
    length = {
        ("zh", "daily"): "15 行以内，手机一屏能看完", ("zh", "weekly"): "一页以内，重点成果最多 5 条",
        ("en", "daily"): "under 15 lines, fits one phone screen", ("en", "weekly"): "one page max, at most 5 key results",
    }[(lang, kind)]
    head = INSTRUCTIONS[lang].format(kind=names[lang][kind], length=length, template=TEMPLATES[(lang, kind)])
    extra = []
    if cfg.get("author_name"):
        extra.append(f"author: {cfg['author_name']}")
    if cfg.get("audience"):
        extra.append(f"audience: {cfg['audience']}")
    data = json.dumps(compact(report), ensure_ascii=False, indent=1)
    return "\n\n".join([
        MARKER, head, *extra,
        "<GUIDE>\n" + guide(lang) + "\n</GUIDE>",
        "<DRAFT note=\"mechanical draft generated from DATA, for reference only\">\n" + draft(report, lang) + "\n</DRAFT>",
        "<DATA>\n" + data + "\n</DATA>",
    ])


def detect(choice: Optional[str] = None) -> Optional[str]:
    if choice:
        return choice
    for name in PRESETS:
        if shutil.which(name):
            return name
    return None


class AIError(RuntimeError):
    pass


def _short_error(text: str) -> str:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    errors = [ln for ln in lines if "error" in ln.lower()]
    return (errors or lines or ["unknown error"])[-1][:300]


def run(prompt: str, engine: str, custom: Optional[List[str]] = None, model: Optional[str] = None,
        timeout: int = 600) -> str:
    """Pipe the prompt to an agent CLI in a scratch directory and return its answer."""
    workdir = tempfile.mkdtemp(prefix="report-skill-")
    out_file = os.path.join(workdir, "report.md")
    if custom:
        cmd = list(custom)
    elif engine == "claude":
        cmd = ["claude", "-p"] + (["--model", model] if model else [])
    elif engine == "codex":
        cmd = ["codex", "exec", "--skip-git-repo-check", "--ephemeral", "-s", "read-only",
               "--color", "never", "-o", out_file] + (["-m", model] if model else []) + ["-"]
    else:
        cmd = [engine]
    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=workdir,
                              timeout=timeout, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            raise AIError(_short_error(proc.stderr + "\n" + proc.stdout) or f"exit {proc.returncode}")
        text = Path(out_file).read_text(encoding="utf-8") if os.path.exists(out_file) else proc.stdout
    except FileNotFoundError:
        raise AIError(f"command not found: {cmd[0]}")
    except subprocess.TimeoutExpired:
        raise AIError(f"timed out after {timeout}s")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0].strip()
    if not text:
        raise AIError("empty response")
    return text + "\n"
