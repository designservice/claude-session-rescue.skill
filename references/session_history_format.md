# Session history file format spec

A session history file is a markdown file written to `<project-root>/.claude-session-rescue/<short-id>-<YYYY-MM-DD>.md`. Its purpose is to **rehydrate a future Claude session with the context it needs to continue where the old session left off** — not to be a passive archive.

Design priorities, in order:

1. **Front-load actionable context.** A future Claude opening this file should know the topic, the decisions, and the next step within the first ~30 lines.
2. **Lead with the last topic.** Section 0 is one sentence describing what was being discussed at the end — the single most useful hook for resuming.
3. **Make continuation friction-free.** Include a copy-paste prompt the user can paste into a new session.
4. **Hide the long tail behind a `<details>` block** so it stays available but doesn't bloat context unless explicitly needed.
5. **Match the source language.** If the old session was in Chinese, the file's section headers and prose are in Chinese.
6. **Preserve every bit of original markdown.** Tables, code blocks, nested lists, bold/italic, headers — all of it stays exactly as the original message had it. The transcript should read like the live conversation, not a flattened log.

---

## File structure

The file has these sections in this order:

```markdown
# Session history: <topic-slug>
_来源：`<original-jsonl-path>`_
_生成时间：<YYYY-MM-DD> · 工具：claude-session-rescue_

(NOTE: Don't use `<!-- HTML comments -->` for metadata — many markdown previews
including Claude Code's render them as literal text instead of hiding them.
Use plain italic text at the top instead. It's visible but visually quiet.)

## 0. Last topic (for new-session pickup)

**One sentence** describing what was being discussed at the end of the
session, in the source language. This is the hook a future Claude reads
first to know how to greet the user.

Example: "讨论 RealSYSTEM 怎么包装成腾讯比赛智能 NPC 赛道的可玩 demo"

## 1. Snapshot

A 3–4 line block answering "what was this about":

**Project:** <basename of project root>
**Topic:** <one-sentence summary>
**Status:** <ongoing / paused / blocked / shipped>
**Original session:** `<short-id>` · <date-range>

## 2. Key decisions

Bulleted list of conclusions reached, with timestamps. 3–10 bullets typical.

- <decision in source language> `[<timestamp>]`

## 3. Open questions & next steps

What was unfinished. If the session ended cleanly with no loose ends, write
"无未决事项" / "Nothing pending" — don't fabricate.

- <pending item>

## 4. Files touched

Paths the old session created/modified. Source: extract.py's `files_touched`,
**then verified to actually exist on disk** before listing. Skip non-existent
paths (or annotate them clearly) — don't pretend they're real.

Format: friendly description on one line, absolute path on the next line in
backticks (code style). Group by location category if there are many.

**Don't use `[label](file:///path)` markdown links.** Many preview engines
(Claude Code's preview, GitHub, browser-based viewers) block or strip
`file://` protocol for security — the result is a link that looks clickable
but does nothing. Plain code-formatted absolute paths are honest: they can
be selected/copied universally, and editors like VS Code and Cursor support
Cmd+click on them anyway.

Example:

```markdown
**项目内文件：**

- 主 GDD —— 已写到 Core Fantasy § Ending Image
  `/Users/admin/Documents/Claude/Projects/GameStudio/design/game-concept.md`
- 竞品分析
  `/Users/admin/Documents/Claude/Projects/GameStudio/design/research/2026-04-22-...md`

**项目记忆：**

- `/Users/admin/.claude/projects/-Users-admin-Documents-.../memory/MEMORY.md`
```

## 5. Last exchange

The final user message + assistant response, verbatim with all original
markdown preserved. Lets a future reader drop straight back into context.

Use colored emoji + bold labels — see "Turn formatting" section below.

---

🟩 **你 / You** · <timestamp>

<last user message, with all original markdown intact>

---

🟧 **Claude** · <timestamp>

<last assistant message, with all original markdown intact>

---

## 6. How to continue in a new session

A ready-to-paste prompt. Source language. Example (Chinese):

> 读 `.claude-session-rescue/<this-filename>` 然后从「未决问题与下一步」第一条接着
> 做。我们上次在 [topic]，需要 [next concrete action]。

## 7. Full transcript

<details>
<summary>展开完整对话历史 — 点开展开</summary>

(turns here — see "Turn formatting" below)

</details>
```

---

## Turn formatting (used in section 5 and 7)

Each turn is separated by a horizontal rule (`---`). Speaker labels use colored emoji squares + bold so they pop visually from the message content:

- **User**: 🟩 (green square — cool, complements Claude orange)
- **Claude**: 🟧 (orange square — matches Claude brand color)

Why emoji, not HTML colored spans: many markdown viewers (GitHub, Claude Code's preview, some editors) sanitize out `style` attributes and the colors silently fail to render. Emoji glyphs carry their color natively — they render reliably in every viewer including terminals.

**Chinese sessions:**

```markdown
---

🟩 **你** · 2026-05-11 08:31

[original markdown, fully preserved — tables, code blocks, bold, lists, headers, all of it]

---

🟧 **Claude** · 2026-05-11 08:32

[original markdown, fully preserved — including any ## ### headers Claude used]

---
```

**English sessions:**

```markdown
---

🟩 **You** · 2026-05-11 08:31

[original markdown, fully preserved]

---

🟧 **Claude** · 2026-05-11 08:32

[original markdown, fully preserved]

---
```

**Why "Claude" instead of "Me":** the user reads the file in a *new* session with a *different* Claude instance. "Me" referring to the past Claude is confusing — "Claude" is unambiguous.

**Why colored emoji + bold (not markdown headers, not bold-only, not HTML colors):** Markdown headers collide with the internal `##`/`###` Claude uses in long answers — breaks the document outline. Plain bold blends into all the other bold text in messages. Inline HTML `<span style="color:...">` gets sanitized by GitHub and many preview engines — colors silently disappear. Colored emoji squares carry their color in the glyph itself and render reliably everywhere.

---

<span style="color:#0E7C7B"><strong>你</strong></span> · <sub>2026-05-11 08:31</sub>

[original markdown, fully preserved — tables, code blocks, bold, lists, headers, all of it]

---

<span style="color:#D97757"><strong>Claude</strong></span> · <sub>2026-05-11 08:32</sub>

[original markdown, fully preserved — including any ## ### headers Claude used]

---
```

**English sessions:**

```markdown
---

<span style="color:#0E7C7B"><strong>You</strong></span> · <sub>2026-05-11 08:31</sub>

[original markdown, fully preserved]

---

<span style="color:#D97757"><strong>Claude</strong></span> · <sub>2026-05-11 08:32</sub>

[original markdown, fully preserved]

---
```

**Why "Claude" instead of "Me":** the user reads the file in a *new* session with a *different* Claude instance. "Me" referring to the past Claude is confusing — "Claude" is unambiguous.

**Why HTML colored labels (not markdown headers, not plain bold):** the original messages often contain their own `##` / `###` headers AND lots of `**bold**` text. Markdown headers would collide with the document's outline. Plain bold would blend into all the other bold text in messages. Colored inline HTML gives a distinct, scannable marker that no message content will accidentally match. Renders correctly in GitHub, Obsidian, VS Code/Cursor markdown preview, and most modern viewers. In plain-text viewers that strip HTML, it falls back to readable plain text (just without the color).

---

## Language matching rules

The file's headers and prose are in **one** language — never mixed. Decision procedure:

1. Skim the user's messages in the old session
2. If >70% of meaningful user text is non-English, use that language
3. If user text is roughly bilingual, match the **most recent** user message
4. Code, file paths, and verbatim quotes stay in their original form

**Source-language header reference:**

| Section | English | 中文 | 日本語 |
|---|---|---|---|
| 0 | Last topic | 上次聊到 | 最後の話題 |
| 1 | Snapshot | 概览 | 概要 |
| 2 | Key decisions | 关键决策 | 主な決定事項 |
| 3 | Open questions & next steps | 未决问题与下一步 | 未解決の問題と次のステップ |
| 4 | Files touched | 涉及文件 | 関連ファイル |
| 5 | Last exchange | 最后一轮对话 | 最後のやり取り |
| 6 | How to continue | 如何在新 session 接续 | 新しいセッションでの続け方 |
| 7 | Full transcript | 完整对话历史 | 全文記録 |

For other languages, translate the headers naturally — preserve the *intent*, not the literal English.

---

## What NOT to include

- ❌ Tool call traces (Read, Bash, Edit invocations) — they're noise for context recovery
- ❌ Internal hook output, skill expansion blobs, `<system-reminder>` tags — already filtered by `extract.py`
- ❌ Speculation about what the user "probably wanted" — stick to what was actually said
- ❌ Recommendations for next actions that the user didn't agree to — the file is a record, not a planner
- ❌ Reformatting / "improving" the original messages — preserve every character exactly

---

## Worked example (Chinese, fragment)

```markdown
# Session history: 腾讯游戏大赛参赛策略
<!-- Source: ~/.claude/projects/.../5644313b-2ef8-4efa-a601-118b78b7bb92.jsonl -->

## 上次聊到

讨论 RealSYSTEM 怎么包装成腾讯比赛智能 NPC 赛道的可玩 demo（玩家身份是节目里的卧底记者）。

## 概览

**项目：** GameStudio
**话题：** 腾讯游戏大赛 2026 AI 赛道（9/15 截止）的双项目参赛策略
**状态：** 进行中（双赛道战略已敲定，进入 demo 细节）
**原 session：** `5644313b` · 2026-05-11 08:31 → 2026-05-12 14:37

## 关键决策
- 《库》→ AI 原生赛道（异步生成作为主观设计选择是核心创新点）`[2026-05-11T09:00:44]`
- RealSYSTEM → 智能 NPC 赛道（神经化学状态机命中评审痛点）`[2026-05-11T09:00:44]`
- 不参加叙事重构赛道（导演视角与该赛道要求结构性不匹配）`[2026-05-11T09:43:45]`
- RealSYSTEM 包装为"卧底记者节目"，复用 confessional 系统 `[2026-05-12T14:37:58]`

## 未决问题与下一步
- 《库》demo 时间轴压缩问题（Mirror Mechanism 的魔法天然跨会话）
- RealSYSTEM 需要新建玩家视角 UI（工作量几天，复用现有 confessional 入口）
- 比赛要求的 PPT、宣传图、宣传视频都未开始

## 涉及文件
- `~/.claude/projects/-Users-admin-Documents-Claude-GameStudio/memory/project_concept.md`

## 最后一轮对话

**你** · 2026-05-12 14:36

realsystem 怎么打包成只能 npc 赛道需要的例子呢？

**Claude** · 2026-05-12 14:37

先把赛道要求和 RealSYSTEM 技术逐条对照。

**技术层面已经完全命中**

| 评审关注点 | RealSYSTEM 的实现 |
|---|---|
| 长线交互中人设一致性 | 神经化学状态机 |
| 记忆膨胀/幻觉问题 | affect_valence + mood-congruent 检索 |

[...原始 markdown 完整保留...]

## 如何在新 session 接续

> 读 `.claude-session-rescue/5644313b-2026-05-21.md` 然后从「未决问题与下一步」接着做。
> 我们上次在讨论 RealSYSTEM 怎么包装成卧底记者节目，下一步是设计玩家视角 UI。

## 完整对话历史

<details>
<summary>展开完整对话历史 — 点开展开</summary>

---

**你** · 2026-05-11 08:31

[第一条用户消息，完整 markdown]

---

**Claude** · 2026-05-11 08:32

[第一条 Claude 回复，完整 markdown]

---

[...所有 12 轮...]

</details>
```
