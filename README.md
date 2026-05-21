<div align="center">

# 不想丢对话.skill

<sub>`claude-session-rescue.skill`</sub>

**Claude Code 项目文件夹改名 / 搬家后，把散落的旧对话找回来，并把其中一个加载成可继续聊的上下文。**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent-Agnostic](https://img.shields.io/badge/Agent-Agnostic-blueviolet)](https://skills.sh)
[![Skills](https://img.shields.io/badge/skills.sh-Compatible-green)](https://skills.sh)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Compatible-cc785c)](https://claude.com/claude-code)
[![Python](https://img.shields.io/badge/Python-3.8+-3776ab)](https://www.python.org)

```bash
npx skills add designservice/claude-session-rescue.skill
```

[做什么](#做什么) · [怎么用](#怎么用) · [产物长什么样](#产物长什么样) · [亮点](#亮点) · [跨平台](#跨平台)

</div>

---

> 你有没有过这种经历：把项目文件夹换了个位置或者改了个名，再打开 Claude Code，`/resume` 里之前的对话全没了？这个 skill 就是干这个的——把散落在 Claude Code 项目存储里、跟当前项目失联的旧对话找回来，挪到该在的地方，并把你想看的那一段加载成"可继续聊的上下文"。

## 做什么

| 产物 | 适合什么时候用 | 你要做的 |
|---|---|---|
| 🔍 **找到失联对话** | 换路径 / 改文件夹名之后 `/resume` 里找不到旧对话 | 跑 skill，确认要不要把它搬到当前项目 |
| 📝 **简介加载到对话** | 想快速回忆某次讨论：话题、关键决策、未决问题、涉及文件 | 选一个 session，简介立刻显示在对话里 |
| 📄 **完整对话存档** | 想以后还能查、能让新 session 加载、能分享给协作者 | 自动存到 `<项目>/.claude-session-rescue/<id>-<date>.md` |

**常见用法**：

- 项目搬家后所有过去对话都找不到了：**找到失联对话 + 简介 + 存档**
- 想接续某段中断的讨论：**简介 + 存档**（让新 session 读那个文件继续聊）
- 单纯归档 / 备份某段重要对话：**存档**

---

## 怎么用

### 安装

如果你主要在 Claude Code 里用：

```bash
git clone https://github.com/designservice/claude-session-rescue.skill \
  ~/.claude/skills/claude-session-rescue
```

只需要 Python 3.8+，stdlib 够用，无额外依赖。

### 跑

在 Claude Code 里：

```
/claude-session-rescue
```

或者自然语言任意一句：「我刚换了文件夹路径，之前的对话怎么找回来？」「帮我恢复一下上次那个聊设计的 session」「想把上次的对话存一份在本地」——skill 都会触发。

也可以直接指定 session id：

```
/claude-session-rescue 28df8c9e
```

### 流程

| Phase | 做什么 | 用户操作 |
|---|---|---|
| 1. 找散落对话 | 探测当前项目同名但路径不同的孤儿目录 | 确认要不要迁移 |
| 2. 列出对话 | 当前项目所有 session（含 fork 关系标注） | 选一个 |
| 3. 加载 | 抽取 + 验证 + 渲染 | 看简介，决定下一步 |

如果选的是 fork（共同前缀很长但不是 canonical 版本），skill 会再次确认，避免你加载几乎完全冗余的内容。

---

## 产物长什么样

```text
<项目根>/
└── .claude-session-rescue/
    └── <短-uuid>-<YYYY-MM-DD>.md   ← 完整对话历史文件
```

每个文件 9 个章节：

```markdown
# Session history: <主题>
_来源：<原 jsonl 路径>_
_生成时间：<日期> · 工具：claude-session-rescue_

## 上次聊到            ← 一句话 hook，新 session 一眼接续

## 概览                ← 项目 / 话题 / 状态 / 原 session 元信息

## 关键决策            ← 带时间戳的决策列表

## 未决问题与下一步    ← 没聊完的、待办的

## 涉及文件            ← 绝对路径，编辑器里 Cmd+click 直接开

## 最后一轮对话         ← 末尾对话原文（带 🟩/🟧 颜色标签）

## 如何在新 session 接续 ← 可直接粘贴的 prompt

## 完整对话历史         ← 全部 53/189/... 轮原文，每轮 --- 分隔
```

新 Claude session 想接续？告诉它读这个文件，然后从「未决问题与下一步」第一条接着干。

---

## 亮点

这个 skill 不只是"导出 jsonl"——它在几个隐藏的坑上做了功课。

### 1. 自动跟随项目迁移

当你把项目文件夹改名或挪位置，Claude Code 的旧 session 文件留在原 encoded dir 里失联。skill 自动探测「同名 basename 但路径不同」的孤儿目录，迁移时一起搬：

- ✅ jsonl 文件（重写内部所有路径引用，不只是 cwd 字段）
- ✅ `memory/` 子目录（Claude Code 的项目记忆）
- ✅ 旧目录归档为 `.trash-<timestamp>`，永不删除，可回滚

### 2. 检测 fork、避免加载冗余对话

Claude Code 偶尔会把一段对话存到两个 jsonl 里（一个被中断、一个继续完成）。它们前 N 轮完全相同，后面分叉。普通工具会把它们当独立 session 列出，你要分别 recall 两遍，看到 99% 相同的内容。

这个 skill 用前 10 轮的 fingerprint 检测 fork 关系，列表里标注「fork of X, 共同前缀 49 轮，独有 2 轮」，并把最长的那个设为 canonical。如果你选了非 canonical 的那个，会再次确认。

### 3. 自动语言匹配

旧 session 是中文聊的就用中文写简介；英文是英文。靠 CJK 字符比例判断主导语言，标签 `🟩 你`（teal 绿）和 `🟧 Claude`（橘红，匹配 Claude 品牌色）。中英以外的语言按原则翻译章节名。

### 4. 路径与 skill 引用全部验证

旧对话里 Claude 说"我已经写到 `path/to/foo.md`"——但那个文件早就移到了别处。这个 skill 扫 transcript 里**每一个**路径和 skill 命令引用，验证存在性：

- 路径存在 → 不动
- 路径不存在但有唯一匹配（同名文件在别处）→ 标注 `⚠️ 实际位于 /绝对路径`
- 路径不存在且无匹配 → 标注 `⚠️ 此文件未找到`
- skill 引用如 `/start` `/brainstorm` `/setup-engine` → 验证 `~/.claude/skills/<name>/SKILL.md` 是否存在

`templates/`、`examples/`、`samples/`、`boilerplate/` 等目录里的同名文件自动过滤（几乎从来不是用户在找的真实文件）。

### 5. 输出格式给 markdown viewer 友好

很多 markdown preview 引擎 sanitize 掉 HTML，所以这个 skill：

- 不用 `<!-- HTML 注释 -->`（很多 viewer 显示成可见文字）
- 不用 `<span style="color:...">`（颜色被 sanitize，标签变孤儿文字）
- 不用 `[label](file:///path)`（很多 viewer 禁用 `file://` 协议，链接看着可点其实不能点）
- 不用 `<details>` 折叠（同样 HTML 风险）

改用：颜色 emoji 表示发言人、纯代码格式绝对路径、内嵌 header 自动降级避免撞文档大纲。

### 6. 一个对话一次 recall

加载两段旧对话到同一个新 session 会让上下文混乱（两套决策、两套"上次聊到"）。skill 强制每个新 session 只 recall 一次。需要看另一段？开新 session。

---

## 跨平台

不绑定 Claude Code。仓库里放了几个轻量入口文件让其他 agent 也能用同一套流程：

| Agent | 入口文件 |
|---|---|
| Claude Code / skills.sh | `SKILL.md` |
| Codex / OpenAI Codex CLI | `AGENTS.md` |
| Gemini CLI | `GEMINI.md` |

每个入口文件只有几行，告诉对应 agent 去读 `SKILL.md`。能力名映射（`Bash` / `Read` / `Write` / `AskUserQuestion` 怎么对应到你那个平台的工具）写在 `AGENTS.md` 里。

`scripts/*.py` 都是独立可调用的：

```bash
python3 scripts/find_orphans.py
python3 scripts/migrate.py --orphan <dir> --old-cwd <path> --new-cwd <path>
python3 scripts/list_sessions.py --dir <encoded_project_dir>
python3 scripts/extract.py <session.jsonl> --format markdown --demote 2 --verify-paths $(pwd)
```

`references/session_history_format.md` 是输出格式 spec，能告诉任何 agent 怎么写这种文件。

---

## 致谢

这个 skill 的设计教训大多来自自己踩坑：HTML 注释不被 markdown 剥离、`file://` 协议被 sanitize、`<span style>` 颜色被去除、Python `\w` 在 CJK 上下文里误判、`templates/` 目录干扰 fuzzy search、forked sessions 不容易识别…… 每个都在 `SKILL.md` 的「Why the design looks like this」章节里记了来由，方便 contributor 不重蹈覆辙。

设计灵感与 README 风格参考自 [`lazy-english-reader.skill`](https://github.com/designservice/lazy-english-reader.skill)。

---

<div align="center">

MIT License © designservice

</div>
