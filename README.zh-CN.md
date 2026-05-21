<div align="center">

# 不想丢对话.skill

<sub>`claude-session-rescue.skill`</sub>

**项目文件夹搬了家？对话跟着走，接着上回聊。**

[English](README.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent-Agnostic](https://img.shields.io/badge/Agent-Agnostic-blueviolet)](https://skills.sh)
[![skills.sh](https://img.shields.io/badge/skills.sh-Compatible-green)](https://skills.sh)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Compatible-cc785c)](https://claude.com/claude-code)
[![Python](https://img.shields.io/badge/Python-3.8+-3776ab)](https://www.python.org)

```bash
npx skills add designservice/claude-session-rescue.skill
```

[为什么需要它](#为什么需要它) · [它做什么](#它做什么) · [安装](#安装) · [使用](#使用) · [输出](#输出)

</div>

---

## 为什么需要它

你改了个文件夹名，或者把项目挪了个位置，Claude Code 就不让你继续之前的对话了。

其实它们还在磁盘上——只是留在了旧路径下面。这个 skill 会自动找到它们、把文件迁移过来、总结上次聊到哪，然后整理成一份 markdown 上下文，在新 session 里接着做。

适合这些情况：

- 项目搬家或改名后，之前的对话不能继续了。
- 想接着某段中断的 Claude Code 讨论继续做。
- 想把重要对话归档成本地 markdown。
- 想给新的 agent session 一个清楚、可验证的交接文件。

> 默认安全：迁移前会先确认，旧目录不会直接删除，而是归档为可回滚的 `.trash-*`，恢复出的历史文件会写在当前项目里。

## 前后对比

| 之前 | 之后 |
|---|---|
| `/resume` 里没有需要的旧 session | 找到并列出失联 session |
| Claude Code 对话留在旧项目路径下 | 选中的项目存储迁移到当前路径 |
| 不知道哪个 JSONL 才是要找的那段工作 | 每个 session 都有话题、决策、文件和最后一轮对话摘要 |
| 新 agent session 没有清楚 handoff | 生成可继续读取的 markdown 归档 |

## 它做什么

| 产物 | 适合什么时候用 | 你会得到什么 |
|---|---|---|
| **找到失联对话** | 换路径后旧 session 不能继续 | 孤儿项目目录候选项和安全迁移确认 |
| **加载对话简介** | 想快速知道上次聊到哪里 | 话题、关键决策、未决问题、涉及文件、最后一轮对话 |
| **归档完整历史** | 需要 handoff、备份或长期检索 | `.claude-session-rescue/` 下的完整 markdown transcript |

它不只是导出 JSONL。它处理了恢复对话时真正容易出错的地方：

- 迁移 session 时重写内部旧项目路径；
- 保留 Claude Code 的项目 memory 目录；
- 检测 forked sessions，并标出最长的 canonical 版本；
- 验证 transcript 里提到的文件路径和 skill 引用；
- 生成对 markdown preview 友好的格式，避免 HTML、`file://`、隐藏注释等兼容性问题；
- 全程只处理本地文件，不上传任何内容。

## 安装

### Claude Code

```bash
git clone https://github.com/designservice/claude-session-rescue.skill \
  ~/.claude/skills/claude-session-rescue
```

只需要 Python 3.8+，不需要额外依赖。

### skills.sh

```bash
npx skills add designservice/claude-session-rescue.skill
```

## 使用

在 Claude Code 里运行：

```text
/claude-session-rescue
```

也可以直接用自然语言触发：

```text
我刚把项目文件夹换了路径，之前的 Claude 对话不见了，帮我找回来。
```

如果已经知道 session id：

```text
/claude-session-rescue 28df8c9e
```

## 流程

| 阶段 | 做什么 | 你要做什么 |
|---|---|---|
| 1. 检测孤儿目录 | 找到同名项目但旧路径下的 Claude Code 存储目录 | 确认是否迁移 |
| 2. 列出 session | 展示当前项目的所有 session，并标注 fork 关系 | 选一段对话 |
| 3. 抽取上下文 | 总结、验证、渲染为 markdown | 阅读简介，或从归档继续接上 |

如果你选的是非 canonical fork，skill 会再次确认，避免把几乎重复的上下文加载进新对话。

## 输出

```text
<项目根>/
└── .claude-session-rescue/
    └── <短-uuid>-<YYYY-MM-DD>.md
```

每个归档文件包含：

- 上次聊到哪里；
- 项目和 session 元信息；
- 关键决策；
- 未决问题与下一步；
- 涉及文件和路径验证说明；
- 最后一轮对话；
- 可直接粘贴的新 session 接续 prompt；
- 完整对话历史。

新 Claude session 想接续时，让它读取这个 markdown 文件，并从「未决问题与下一步」第一条开始。

## 跨 Agent 支持

仓库里包含几个轻量入口文件：

| Agent | 入口文件 |
|---|---|
| Claude Code / skills.sh | `SKILL.md` |
| Codex / OpenAI Codex CLI | `AGENTS.md` |
| Gemini CLI | `GEMINI.md` |

所有核心脚本都是独立 Python：

```bash
python3 scripts/find_orphans.py
python3 scripts/migrate.py --orphan <dir> --old-cwd <path> --new-cwd <path>
python3 scripts/list_sessions.py --dir <encoded_project_dir>
python3 scripts/extract.py <session.jsonl> --format markdown --demote 2 --verify-paths "$(pwd)"
```

`references/session_history_format.md` 是输出格式 spec，方便其他 agent 读取或生成同类 session history 文件。

## 限制

- 只能从本机 Claude Code session 文件恢复，不能恢复从未保存到本地的对话。
- 需要访问 `~/.claude/projects/`。
- 它从 transcript 重建上下文，不会恢复隐藏的模型状态。
- 不建议把多个旧 session 加载进同一个新对话，因为不同决策和下一步容易混在一起。

## 隐私

不想丢对话.skill 不会把对话内容发到任何外部服务。它只读取本机 `~/.claude/projects/` 下的 JSONL，归档写到当前项目的 `.claude-session-rescue/`，迁移后的旧目录会以 `~/.claude/projects/.trash-*` 形式保留，方便回滚。

---

<div align="center">

MIT License © designservice

</div>
