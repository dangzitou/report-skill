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

**安装只需要一句话。** 把下面这句发给你的 Claude Code / Codex / ZCode：

```text
帮我安装 report-skill：https://raw.githubusercontent.com/dangzitou/report-skill/main/INSTALL.md
```

装好之后，跟它说「写今天的日报」或者「把上周的周报发给老板」就行。

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

## 安装

### 方式一：让 Agent 帮你装（推荐）

把这句话发给任意一个编程 Agent（Claude Code、Codex、ZCode、OpenCode、Cursor……）：

```text
帮我安装 report-skill：https://raw.githubusercontent.com/dangzitou/report-skill/main/INSTALL.md
```

[INSTALL.md](INSTALL.md) 是专门写给 Agent 看的安装手册。Agent 会按步骤完成以下几件事：

1. 安装 CLI，会自动选择 uv、pipx 或私有 venv 中能用的那一种；
2. 把 skill 装进本机所有 Agent 的 skills 目录；
3. 验证能读到哪些数据；
4. 如果你用飞书，还会帮你接上。

整个过程中只有飞书授权需要你在浏览器里点一下，其余都由 Agent 完成。

### 方式二：自己装，一行命令

```bash
curl -fsSL https://raw.githubusercontent.com/dangzitou/report-skill/main/install.sh | sh
```

这行命令会顺便执行 `report-skill setup`，把 skill 装进 Claude Code、Codex、ZCode、OpenCode 以及 `~/.agents`，并生成配置。重复运行是安全的，也可以当作升级用。Windows 用户可以用 `uv tool install "report-skill @ git+https://github.com/dangzitou/report-skill"`，装好后再运行 `report-skill setup`。

## 使用

### 在 Agent 里（推荐）

> 写今天的日报 / 写上周的周报，语气正式一点 / 把本周周报发给 leader / 存成飞书文档 / what did I do this week?

Agent 会先运行 `report-skill <时间> --prompt`，拿到事实和写作规范，然后亲自写出报告，你可以接着让它改。如果你让它发出去，它会调用 `report-skill send`。

### 在终端里

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

### 对 Agent 友好的设计

- **从不卡在交互上**：不是在终端里运行时（stdin 不是 TTY）绝不会弹出询问。
- **机器可读**：`setup`、`doctor`、`send` 都支持 `--json`。
- **退出码**：`0` 成功；`1` 出错，JSON 里的 `fix` 字段会给出修复命令；`2` 参数不对；`3` 需要用户同意，Agent 问过用户后加 `--yes` 重跑即可。
- **改配置不用编辑 JSON**：`report-skill config set lark.send_to leader`。
- **发送 Agent 自己写的报告**：`report-skill send report.md --to-lark leader --yes --json`。

## 读哪些数据

| 来源 | 位置 | 读什么 |
| --- | --- | --- |
| Claude Code | `~/.claude/projects/*/*.jsonl` | 你的提问、会话标题、改过的文件 |
| Codex（CLI / Desktop） | `~/.codex/sessions/**/rollout-*.jsonl` | 你的提问、线程名、`apply_patch` 改过的文件 |
| ZCode | `~/.zcode/cli/db/db.sqlite` | 你的提问、任务标题、改过的文件 |
| git | 上面这些会话涉及的仓库，以及你配置的目录 | **你自己的**提交、改动行数（会自动合并 worktree） |
| 飞书 / Lark（可选） | 通过官方 [lark-cli](https://github.com/larksuite/cli) | 参加的会议、完成的任务、即将到期的任务 |

所有读取都是**只读**的。它会先过滤掉 Agent 自动注入的系统提示、`AGENTS.md`、工具输出这类噪音，只保留你亲手打的字。

## 飞书 / Lark：读日程和任务，一键发给领导

如果你装了官方的 [lark-cli](https://github.com/larksuite/cli)，report-skill 会自动接入，不用额外配置：

- **读**：从日历读取你参加的会议（已拒绝的会自动跳过），从任务读取期间完成的任务，以及即将到期的任务。完成的任务会作为“已完成”的证据写进成果；即将到期的任务会直接成为「明日计划 / 下周计划」，并保留截止日期。这样计划一栏就不用再空着让你自己填了。
- **发**：报告写好后，可以直接发到飞书，或者存成一篇飞书云文档。

```bash
# 一次性准备：安装并登录 lark-cli
npx @larksuite/cli@latest install
lark-cli auth login --domain calendar,task,im,docs

report-skill --to-lark me                   # 先发给自己当草稿（不需要确认）
report-skill --to-lark ou_xxxxxxxx          # 私聊发给某人（open_id）
report-skill week --to-lark oc_xxxxxxxx     # 发到群（chat_id）
report-skill week --to-lark leader          # 用配置里的别名
report-skill week --lark-doc                # 存成飞书云文档，并输出链接
report-skill --to-lark leader --dry-run     # 只预览请求，不真的发送
```

发给别人的消息会被看到，所以**除了发给自己，发送前一定会先问你确认**。在脚本或定时任务里不方便交互时，需要显式加上 `--yes`。默认以你本人的身份发送（`--as user`）。如果想用机器人身份发，在配置里把 `lark.identity` 设为 `"bot"`，并确保机器人已经在目标群里。

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

不配置也能用。所有设置都可以用命令改，比如 `report-skill config set lang zh`、`report-skill config set lark.targets.leader ou_xxx`，也可以直接让 Agent 帮你改。配置文件在 `~/.config/report-skill/config.json`，所有键都是可选的：

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
  "sources": ["claude-code", "codex", "zcode", "git", "lark"],
  "lark": {
    "identity": "user",                 // 以谁的身份调用 lark-cli：user | bot
    "include": ["calendar", "tasks"],   // 从飞书读什么
    "targets": {"leader": "ou_xxx", "team": "oc_xxx"},  // --to-lark 的别名
    "send_to": "leader",                // 只写 --to-lark 不带参数时的默认对象
    "doc_folder": null                  // --lark-doc 存到哪个文件夹 / 知识库节点
  },
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

**飞书的 open_id / chat_id 去哪找？**
可以运行 `lark-cli contact +search-user --query 张三` 和 `lark-cli im +chat-search --query 项目群`，或者直接在 Agent 里让它用 lark-cli 帮你查。

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
