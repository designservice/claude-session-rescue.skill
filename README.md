<div align="center">

# Claude Session Rescue

<sub>`claude-session-rescue.skill` · 不想丢对话</sub>

**Don't lose the conversation. Recover Claude Code sessions after moving, renaming, or reopening a project from a different path.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent-Agnostic](https://img.shields.io/badge/Agent-Agnostic-blueviolet)](https://skills.sh)
[![skills.sh](https://img.shields.io/badge/skills.sh-Compatible-green)](https://skills.sh)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Compatible-cc785c)](https://claude.com/claude-code)
[![Python](https://img.shields.io/badge/Python-3.8+-3776ab)](https://www.python.org)

```bash
npx skills add designservice/claude-session-rescue.skill
```

[Why it exists](#why-it-exists) · [What it does](#what-it-does) · [Install](#install) · [Usage](#usage) · [Output](#output) · [Chinese](#中文版)

</div>

---

## Why It Exists

Claude Code stores project sessions under an encoded project path. Rename a folder, move the project, or open it from a different absolute path, and old conversations can vanish from `/resume` even though the raw session files still exist on disk.

**Claude Session Rescue finds those stranded sessions, migrates them back to the current project, and turns one selected conversation into clean continuation context.**

Use it when:

- `/resume` no longer shows conversations after a project move or rename.
- You need to continue a past Claude Code session without rereading raw JSONL.
- You want a durable local archive of an important conversation.
- You are handing work to a new agent session and need a concise, verified handoff file.

> Safe by default: the skill asks before migration, archives old directories instead of deleting them, and writes recovered histories into your project.

## Before / After

| Before | After |
|---|---|
| `/resume` shows no useful old sessions | Orphaned sessions are found and listed |
| Claude Code conversations are stranded under a previous project path | Selected project storage is migrated to the current path |
| You do not know which JSONL file contains the work you need | Each session is summarized with topic, decisions, files, and last exchange |
| A new agent session has no clean handoff | A markdown archive is saved for continuation |

## What It Does

| Outcome | When you need it | What you get |
|---|---|---|
| **Find stranded sessions** | Old conversations disappeared after the project path changed | Candidate orphan project directories and a safe migration prompt |
| **Load a session summary** | You want to remember what happened in a previous conversation | Topic, decisions, open questions, files touched, and the last exchange |
| **Archive full history** | You need a handoff or permanent record | A markdown file under `.claude-session-rescue/` with the complete transcript |

This is more than a JSONL exporter. It handles the boring edge cases that usually make rescued context unreliable:

- rewrites moved project paths inside migrated session files;
- preserves Claude Code project memory folders;
- detects forked sessions and highlights the canonical longest version;
- verifies file paths and skill references mentioned in the transcript;
- writes markdown that survives strict preview engines without fragile HTML, `file://` links, or hidden comments;
- keeps everything local.

## Install

### Claude Code

```bash
git clone https://github.com/designservice/claude-session-rescue.skill \
  ~/.claude/skills/claude-session-rescue
```

Requires Python 3.8+. No third-party packages are needed.

### skills.sh

```bash
npx skills add designservice/claude-session-rescue.skill
```

## Usage

In Claude Code:

```text
/claude-session-rescue
```

Natural language works too:

```text
I moved this project and my old Claude sessions disappeared. Help me recover them.
```

You can also target a known session id:

```text
/claude-session-rescue 28df8c9e
```

## Workflow

| Phase | What happens | Your action |
|---|---|---|
| 1. Detect orphans | Finds same-name project directories stored under older paths | Confirm whether to migrate |
| 2. List sessions | Shows sessions for the current project, including fork relationships | Pick one conversation |
| 3. Extract context | Summarizes, verifies, and renders the selected session | Read the summary or continue from the archive |

If you choose a non-canonical fork, the skill asks for confirmation before loading near-duplicate context.

## Output

```text
<project-root>/
└── .claude-session-rescue/
    └── <short-uuid>-<YYYY-MM-DD>.md
```

Each generated archive includes:

- what the last session was about;
- project and session metadata;
- key decisions;
- open questions and next steps;
- files mentioned, with path verification notes;
- the final exchange;
- a ready-to-paste continuation prompt;
- the complete conversation history.

To continue in a new Claude session, ask it to read the generated markdown file and start from the first item under "Open questions and next steps."

## Cross-Agent Support

The repository includes lightweight entry files for multiple agent runtimes:

| Agent | Entry file |
|---|---|
| Claude Code / skills.sh | `SKILL.md` |
| Codex / OpenAI Codex CLI | `AGENTS.md` |
| Gemini CLI | `GEMINI.md` |

The Python scripts are standalone and can be called directly:

```bash
python3 scripts/find_orphans.py
python3 scripts/migrate.py --orphan <dir> --old-cwd <path> --new-cwd <path>
python3 scripts/list_sessions.py --dir <encoded_project_dir>
python3 scripts/extract.py <session.jsonl> --format markdown --demote 2 --verify-paths "$(pwd)"
```

`references/session_history_format.md` documents the archive format for agents that need to generate or consume session history files.

## Limitations

- Works from local Claude Code session files; it cannot recover conversations that were never saved locally.
- Requires filesystem access to `~/.claude/projects/`.
- Reconstructs context from saved transcripts; it does not recreate hidden model state.
- Loading multiple old sessions into one new chat is intentionally discouraged because it can mix conflicting decisions and next steps.

## Privacy

Claude Session Rescue never sends session data to an external service. It only reads local JSONL files under `~/.claude/projects/`, writes archives under the current project, and may archive migrated orphan directories as `~/.claude/projects/.trash-*` for rollback.

---

## 中文版

<div align="center">

# Claude Session Rescue

<sub>`claude-session-rescue.skill` · 不想丢对话</sub>

**Claude Code 项目文件夹改名、搬家、换路径后，把 `/resume` 里消失的旧对话找回来，并整理成可继续聊的上下文。**

</div>

## 为什么需要它

Claude Code 会按项目的绝对路径存储 session。项目文件夹一改名、一搬家，或者从另一个路径重新打开，旧对话就可能不再出现在 `/resume` 里。它们通常没有丢，只是留在了旧路径对应的项目存储目录里。

**Claude Session Rescue 会找到这些失联 session，安全迁移到当前项目，并把你选中的一段对话整理成可接续的 markdown 上下文。**

适合这些情况：

- 项目搬家或改名后，`/resume` 里看不到过去的对话。
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
| **找到失联对话** | 换路径后旧 session 消失 | 孤儿项目目录候选项和安全迁移确认 |
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

Claude Session Rescue 不会把对话内容发到任何外部服务。它只读取本机 `~/.claude/projects/` 下的 JSONL，归档写到当前项目的 `.claude-session-rescue/`，迁移后的旧目录会以 `~/.claude/projects/.trash-*` 形式保留，方便回滚。

---

<div align="center">

MIT License © designservice

</div>
