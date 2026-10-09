<div align="center">

# report-skill

**别再对着空白文档回忆人生了。**
根据你本机的 Claude Code / Codex / ZCode 对话记录和 git 提交，一条命令写出领导 30 秒就能看懂的日报和周报。

[English](README.md) · **简体中文**

[![CI](https://github.com/dangzitou/report-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/dangzitou/report-skill/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

周五 17:50，你打开空白文档，开始想：**这周到底干了啥？**

周一周二的事已经记不清了，只好去翻聊天、翻提交、翻笔记。结果最近两天写得特别细，前面的事全漏了。好不容易憋完发出去，领导回了一句“没重点”。

其实你这周做的事，你的 AI Agent 都记着：每一句「帮我修这个 bug」、每一次改动的文件、每一个 commit。**report-skill 读取这些本地记录，按照大厂汇报的写法整理成报告**：结论先行，写结果不写过程，问题带方案，计划带节点。

```bash
report-skill          # 今天的日报
report-skill week     # 本周周报
```

## 效果

<table>
<tr><th>它读到的（你的原始记录）</th><th>它写出来的</th></tr>
<tr><td>

```text
[Claude Code] 订单导出接口超时了，帮我看看
[Claude Code] 加个分页，再补一下测试
[Codex]       写个脚本批量回填历史订单的 region 字段
[ZCode]       压测一下导出接口
[ZCode]       帮我改一下简历第二段   ← 不该给领导看
[git] fix(export): paginate order export (#212)
      +184 −37
[git] chore: backfill region for legacy orders
```

</td><td>

```markdown
# 工作日报 · 2026-10-08 周四
**一句话总结**：订单导出超时已修复并补齐测试，
历史订单 region 回填脚本完成；约 6 小时。

## 今日完成
1. 【订单导出】接口改为分页导出，修复大客户
   导出超时，已补单测（#212，+184/−37）
2. 【数据修复】完成历史订单 region 字段回填
   脚本，[待确认：回填条数]

## 风险 / 需要支持
- 压测结果待出，[待补充：是否需要 DBA 协助]

## 明日计划
1. 周五中午前完成导出接口压测，输出报告
```

</td></tr>
</table>

> 示例为虚构数据。注意两点：简历相关的对话被自动略去；所有材料里没有的数字，都标成了 `[待确认]`，不会编。

## 30 秒上手

```bash
# 安装（任选一种；零依赖，Python 3.9+）
uv tool install git+https://github.com/dangzitou/report-skill
pipx install git+https://github.com/dangzitou/report-skill

# 不装也能先试试
uvx --from git+https://github.com/dangzitou/report-skill report-skill
```

不需要任何配置。它会自动找到本机的 Agent 记录，用你全局的 git 身份筛出你自己的提交，然后调用本机已经装好的 `claude` 或 `codex` CLI 把事实写成报告。如果都没装，它会输出一份排好版的离线草稿。

```bash
report-skill                 # 今天的日报（凌晨 4 点前的加班算前一天）
report-skill yesterday       # 昨天
report-skill week            # 本周周报
report-skill last-week       # 上周
report-skill 2026-10-01      # 指定某天
report-skill --since 2026-09-01 --until 2026-09-30   # 月报 / 自定义区间

report-skill week -c         # 生成后直接复制到剪贴板
report-skill --raw           # 不调用 AI，只输出离线草稿（秒出）
report-skill --lang en       # 指定语言（默认跟随你平时打字的语言）
report-skill doctor          # 看看都找到了哪些数据源
```

## 在 Agent 里用：说一句「写日报」就行

```bash
report-skill install-skill
```

这条命令会把 skill 装进 `~/.claude/skills`、`~/.codex/skills` 和 `~/.zcode/skills`（只装本机存在的）。之后在 Claude Code、Codex 或 ZCode 里直接说：

> 帮我写今天的日报 / 写上周的周报，语气正式一点 / what did I do this week?

Agent 会自己调用 `report-skill`，拿到事实和写作规范，然后当场写出来，你还可以接着让它改。

## 读哪些数据

| 来源 | 位置 | 读什么 |
| --- | --- | --- |
| Claude Code | `~/.claude/projects/*/*.jsonl` | 你的提问、会话标题、改过的文件 |
| Codex（CLI / Desktop） | `~/.codex/sessions/**/rollout-*.jsonl` | 你的提问、线程名、`apply_patch` 改过的文件 |
| ZCode | `~/.zcode/cli/db/db.sqlite` | 你的提问、任务标题、改过的文件 |
| git | 上面这些会话涉及的仓库，以及你配置的目录 | **你自己的**提交、改动行数（会自动合并 worktree） |

所有读取都是**只读**的。它会先过滤掉 Agent 自动注入的系统提示、`AGENTS.md`、工具输出这类噪音，只保留你亲手打的字。

## 为什么它写得像样：一份写进 prompt 的汇报方法论

我们在小红书上翻了 20 多篇高赞笔记（作者有大厂产品、研发主管、实习转正的同学），加上金字塔原理、PREP、SCQA 等经典方法，整理成了一份[写作指南](report_skill/skill/references/guide.zh.md)。AI 每次都必须按它来写。几个最关键的点：

- **领导只有 30 秒**，他只想知道三件事：进度、问题、计划。所以第一行必须是一句话总结。
- **日报讲事实，周报讲变化，月报讲意义。** 周报不是把五天日报拼起来。
- **写结果，不写过程。** 不写“写了登录模块”，要写“登录模块支持验证码登录，自测通过”。
- **数字往时间和钱上靠**，领导只对两类数有反应：花了多少、省了多少。
- **写你挡住了什么。** “本周零故障”比“处理了 12 个工单”更能让领导安心。
- **让领导做选择题。** 问题要写成「现象 → 原因 → 两个方案 + 倾向 → 需要的支持」。
- **计划要可验收。** 只写 1–3 件，每件带交付物和时间节点，“继续推进”不算计划。
- **表达能力 = 可见度。** 很多人不是没做好，只是没被看见。

此外还有 AI 专属的红线：**不编造**（缺的就写 `[待确认]`），**不夸大**（改个参数别写成“优化系统性能”），**不写不该给领导看的**（求职、私事），**脱敏**（密钥、token 自动打码）。

## 隐私

- 默认不联网。数据只在本机读取。
- 只有在调用 AI 写作那一步，整理后的摘要才会交给**你自己已经在用的** `claude` 或 `codex` CLI，走的是你原本的账号和配置。用 `--raw` 可以完全离线。
- 提问内容和提交信息里像 API Key、token、密码、私钥的字符串，会在进入报告和 prompt 之前被打码。
- 用 Codex 写报告时带了 `--ephemeral` 参数，不会在你的历史里多出一条会话；用 Claude 写时会话带标记，下次生成时会自动跳过。

## 配置（可选）

不配置也能用。如果需要配置，运行 `report-skill init` 生成 `~/.config/report-skill/config.json`：

```jsonc
{
  "lang": "zh",                         // 不填就跟随你平时打字的语言
  "ai": "codex",                        // claude | codex，不填则自动选
  "ai_model": "gpt-5.5",                // 传给 CLI 的模型
  "authors": ["me@company.com"],        // git 作者，不填用全局 user.email / user.name
  "scan_roots": ["~/work"],             // 额外扫描这些目录下的仓库
  "repos": ["~/work/infra"],            // 总是包含的仓库
  "exclude": ["*/playground/*"],        // 不想出现在报告里的项目
  "aliases": {"/Users/me/work/svc-ord": "订单服务"},  // 项目显示名
  "day_start_hour": 4,                  // 几点之前算前一天
  "sources": ["claude-code", "codex", "zcode", "git"],
  "author_name": "小王",
  "audience": "直属领导"
}
```

也可以完全自定义 AI 命令，prompt 会通过 stdin 传入：`"ai_command": ["ollama", "run", "qwen3"]`。

## 常见问题

**会把我花三小时改简历的事写进日报吗？**
不会。prompt 里明确要求 AI 略去求职、简历、面试和私人事务。如果还是不放心，可以用 `exclude` 把整个目录排除掉。

**“投入时长”是怎么算的？**
它按你的活动时间点（提问、改文件、提交）计算间隔，超过 30 分钟没有动静就算中断。这只是一个估算，报告里最多写“约 X 小时”。

**同时开了好几个会话，时间会重复算吗？**
总时长是把所有事件放在同一条时间线上算的，不会重复。分项目的时长是各自单独算的，所以加起来可能比总时长多。

**我用的是 Cursor / Gemini CLI / OpenCode……**
欢迎提 [issue](https://github.com/dangzitou/report-skill/issues/new?template=new_source.md) 或 PR。一个 collector 大约 80 行，可以参考 [`claude_code.py`](report_skill/collectors/claude_code.py)。

**生成的报告能直接发吗？**
建议发出前花 1 分钟看一遍，把 `[待确认]` 的地方补上。AI 负责整理事实，人负责确认事实。

## 参与贡献

```bash
git clone https://github.com/dangzitou/report-skill && cd report-skill
python3 -m unittest discover -s tests -t .
python3 -m report_skill --raw
```

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## License

[MIT](LICENSE)
