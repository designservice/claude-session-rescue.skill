---
name: claude-session-rescue
version: 0.2.0
description: |
  Rescue prior Claude Code sessions that got stranded after a project folder was moved
  or renamed. Use this skill whenever the user mentions losing chat history, can't find
  old sessions in /resume, moved their project folder, wants to bring past conversation
  context into a new session, or wants to archive/export Claude conversations as markdown
  — even if they don't explicitly say 'rescue' or use the slash command.
  Finds orphaned sessions, lets the user pick one, generates a summary in the
  conversation's original language, and saves a full conversation export to the project
  for future reference.
argument-hint: "[session-id-prefix | 'migrate' | 'list' | path-to-jsonl | empty for full flow]"
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
---

# Rescue Prior Session

When a Claude Code project folder gets moved or renamed, the old sessions stay in their original `~/.claude/projects/<encoded-old-path>/` dir and don't show up in `/resume`. This skill puts them back where they belong, lets the user pick one, generates a summary in the conversation's original language, and saves the full conversation to a markdown file for future reference.

## How to talk to the user (READ THIS FIRST)

The user is not a technical person. Every time you narrate what's happening or ask a question, **translate every piece of jargon into plain language**. Examples:

| Don't say | Do say |
|---|---|
| "Phase 1: Detect orphans" | "Looking for old conversations that got left behind when you moved the folder" |
| "Worktree orphan session" | "An old conversation from a temporary working folder you used before" |
| "Rewrite the cwd field" | "Update where the conversation thinks it belongs" |
| "Encoded project dir" | (don't mention it at all — just say "Claude's storage for this project") |
| "Session history file" | "the markdown file with your past conversation" (or just refer to the actual path) |
| "JSONL" | "The conversation file" |

If you must use a technical term because there's no good plain-language substitute, give a one-sentence layman's explanation immediately after.

Same rule applies to `AskUserQuestion`: the question text and every option label should read naturally to someone who has never heard of git, file paths, or JSON.

## The output is always the same

This skill produces **two things together**, every time:

1. A **summary** shown in the conversation (snapshot, key decisions, open questions, files touched, last exchange)
2. A **session history file** written to `<project-root>/.claude-session-rescue/<short-id>-<YYYY-MM-DD>.md` containing the full conversation, formatted for human reading

No mode picker. No "how deep do you want to go" question. Both outputs are cheap to produce and serve different needs (summary = read now, file = read later or feed to a future session).

## One rescue per conversation

Loading two old conversations into the same new session mixes contexts in a way that hurts more than it helps — the new Claude ends up with conflicting decisions, ambiguous "what were we doing" signals, and double the noise. So: do at most one rescue per conversation. If the user asks for a second:

> "I already loaded session `<previous-id>` in this conversation. Loading another would mix things up. Open a new Claude session and run `/claude-session-rescue` there."

---

## Phase 0: Route on argument

| Arg | Goes to |
|---|---|
| empty | Full flow: Phase 1 → 2 → 3 |
| `migrate` | Phase 1 only |
| `list` | Phase 2 only |
| 4+ hex chars (uuid prefix) or full uuid | Phase 3 with the given id |
| ends in `.jsonl` | Phase 3 with the given path |
| anything else | Reply with usage and stop |

`$SKILL_DIR` below means wherever this SKILL.md lives. The default install path is `~/.claude/skills/claude-session-rescue/`.

---

## Phase 1: Look for stranded conversations

**Narrate to the user, plainly:** "Let me first check whether you have any old conversations sitting in other places — when you moved or renamed the folder, some of them might have been left behind."

Run:

```bash
python3 "$SKILL_DIR/scripts/find_orphans.py"
```

The output is JSON with an `orphans` array. If empty, just say "All your past conversations are already where they should be — moving on to the list." and continue to Phase 2.

If non-empty, for each orphan use `AskUserQuestion`. Phrase it in plain language:

- **Question text**: "I found <N> old conversation(s) from <human-readable-description-of-old-path>. The original folder doesn't exist anymore. Want me to move these into your current project so you can see them again?"
- **Options**:
  - "Yes, move them" (default)
  - "Skip this one"
  - "Skip all and continue"

If the orphan is a worktree subfolder (basename contains `worktrees`), add a note: "this one came from a temporary working folder created by a tool like gstack — the conversation content is still useful, but its original location no longer exists."

For each confirmed orphan, run:

```bash
python3 "$SKILL_DIR/scripts/migrate.py" \
  --orphan "<encoded_dir>" \
  --old-cwd "<old_cwd>" \
  --new-cwd "$(pwd)"
```

The script copies each conversation file, **rewrites every occurrence of the old folder path inside the file** (not just the "belongs to this folder" field — also file references inside tool calls and message text, so files in the conversation stay clickable from the new location), and archives the old location with a `.trash-` prefix (so the user can roll back if it was the wrong move).

Then report plainly: "Moved <N> conversation(s) over. The old location is preserved under `.trash-...` in case you ever need to undo this."

---

## Phase 2: Show what's there and let the user pick

**Narrate plainly:** "Here's everything you've discussed with Claude in this project. Pick one and I'll write up a summary."

Run:

```bash
python3 "$SKILL_DIR/scripts/list_sessions.py" \
  --dir "$HOME/.claude/projects/$(pwd | sed 's|/|-|g')" \
  --exclude "<current-session-uuid-if-known>"
```

Identifying the current session is unreliable (no env var for it). If unsure, list everything and warn the user "skip the entry that matches what you're typing right now". The current session is usually the most recent.

Present the list as numbered items. For each, show:

- A short readable date ("May 11, 2026")
- Turn count ("12 turns")
- A one-line **topic hint** — take the first user message and trim to ~80 chars
- **Fork relationship**, if any (see "Fork detection" below)

Use `AskUserQuestion` if 2–4 sessions, freeform reply (id prefix) if more.

If 0 sessions remain, say "Nothing else to load." and stop.

### Fork detection

`list_sessions.py` automatically detects when two sessions share a long common prefix (Claude Code sometimes stores a single logical conversation across multiple jsonl files — e.g., when one is interrupted and another continues). The output fields:

- `is_canonical: true` — this session has the most turns within its fork group; treat it as the "complete" version
- `fork_of: <short_id>` — this session is a shorter fork of another
- `common_prefix_turns: N` — how many turns are byte-identical with siblings
- `divergent_turns: N` — turns unique to this session after divergence
- `fork_siblings: [...]` — short_ids of other sessions in the same group

When narrating, tell the user plainly:

> "**`28df8c9e`** and **`c04c652a`** look like the same conversation captured in two files — they share 49 turns at the start. `28df8c9e` has 2 more turns after that point (looks like the complete version). `c04c652a` also has 2 turns after the split (likely a different ending — perhaps an interrupt). Recommend loading `28df8c9e` unless you specifically want to see the other ending."

Don't auto-hide the shorter fork — the user might want to see its 2 divergent turns (which could include important info like "[Request interrupted]" markers, or a different conversational branch).

---

## Phase 3: Load it

Resolve the chosen session to a file path:

```bash
if [ -f "$ARG" ]; then
  FILE="$ARG"
else
  matches=( "$PROJECT_DIR/$ARG"*.jsonl )
  # 1 match: use it. 0 or >1: tell the user plainly.
fi
```

### 3a. Fork confirmation (BEFORE extracting)

**If the chosen session has `fork_of` set** (i.e. it's a non-canonical fork of a longer sibling), DO NOT proceed silently. Stop and confirm with `AskUserQuestion`:

- **Question text** (plain language, source-language matched): "You picked `<short_id>`. Heads up — this is a shorter fork of `<canonical_id>` (the complete version). They share the first `<common_prefix_turns>` turns; this one has only `<divergent_turns>` unique turns after that. Most of what you'd recall from this one is also in `<canonical_id>`. What do you want to do?"
- **Options**:
  - "Switch to `<canonical_id>` (the complete version, recommended)"
  - "Stay with `<short_id>` — I want to see this fork specifically (e.g. an interrupted ending)"

This catches the case where the user skimmed past the fork annotation in the list. The cost of one extra question is much smaller than the cost of recalling a near-duplicate without knowing.

**If the chosen session is canonical** (or has no fork siblings), don't ask — just proceed to 3b.

### 3b. Narrate and extract

**Narrate plainly:** "Reading the conversation. I'll write a summary in the language you used, and save the full thing as a file so you can come back to it later."

### Extract

Standard command for the full-transcript section of the session history file:

```bash
python3 "$SKILL_DIR/scripts/extract.py" "$FILE" \
  --format markdown \
  --demote 2 \
  --verify-paths "$(pwd)"
```

For the meta block (turn counts, timestamps, files touched):

```bash
python3 "$SKILL_DIR/scripts/extract.py" "$FILE" --format meta
```

For long sessions (>200 turns), add `--tail 80` to the summary pass so the model's working memory isn't bloated. **The session history file always gets the full transcript regardless of size.**

The three flags above are not optional — each fixes a real bug in unguarded output:

- **`--demote 2`**: shifts every `#`/`##`/`###` inside message content down by 2 levels. Claude often uses `##` and `###` headers in long answers; without demotion, those collide with the session history file's own h2 sections and shatter the outline.
- **`--verify-paths PROJECT_ROOT`**: walks every path-like reference in the transcript, verifies existence, annotates wrong ones with ⚠️ pointing at the real location (or "not found"). Catches the common case where Claude said "I wrote X to `path/Y`" but the file ended up elsewhere. Without this, the file looks trustworthy but its references silently lie.
- **(implicit, always on) link stripping**: `[label](local/path)` markdown links to local files get flattened to plain text before path verification — `file://` doesn't render as clickable in most viewers anyway, and leaving the link wrapper around makes path verification mis-annotate it.

### Detect source language

Look at the user's messages. What language are they writing in? Pick that language for **every** label in both the summary and the session history file. If the user wrote mostly Chinese, use 你 / Claude in the file; if English, use You / Claude. Match the most recent user message if it's genuinely bilingual.

This matters because reading a Chinese conversation summarized in English forces the user to mentally translate back, which costs attention they should be spending on remembering the work.

### Write the session history file

Use the Write tool to create `<project-root>/.claude-session-rescue/<short-id>-<YYYY-MM-DD>.md` following `references/session_history_format.md`.

If the file already exists (same id, same date), append a `-1`, `-2` suffix.

If the project is a git repo and `.claude-session-rescue/` isn't in `.gitignore`, mention it once: "Consider adding `.claude-session-rescue/` to your `.gitignore` if you don't want these files committed." Don't add it automatically.

### Show the summary

Use the section names from `references/session_history_format.md` (translated to the source language). Include sections 1–5 (Snapshot, Key decisions, Open questions, Files touched, Last exchange) in chat. Don't include section 7 (full transcript) — that's only in the file.

### End with a clear next-step prompt

The summary closing line must do **two things**:

1. **Surface the affordances** — tell the user what they can do next:
   - Ask any follow-up question about the rescued conversation
   - Say "let's continue" and I'll read the full export file as context and we'll pick up where you left off
   - Or start something completely new — the summary is just reference
2. **Hook on the last topic** — read the last user/assistant exchange and surface what was being discussed, so the user has an obvious "yes, that" reply.

In the source language. Example (Chinese):

> 上面是简介。如果想接着上次的话题聊，告诉我"接着上次聊"，我会把完整对话文件作为上下文。或者你也可以直接问我关于这段历史的任何问题。
>
> 我们上次讨论到 **<last topic, one sentence>**——想从这里继续吗？

Example (English):

> That's the summary. If you want to pick up where you left off, just say "continue from there" and I'll load the full conversation file as context. Or ask me anything about what's above.
>
> We were discussing **<last topic, one sentence>** — want to keep going from there?

Then **stop**. Wait for the user.

---

## Edge cases

| Situation | Handling |
|---|---|
| `python3` not available | Tell the user they need Python 3.8+. Suggest `brew install python` or equivalent. |
| Encoded project dir doesn't exist yet (brand-new project) | "There's nothing to rescue yet — this looks like a fresh project." |
| Orphan dir's `old_cwd` equals current cwd (false positive) | `find_orphans.py` filters these out automatically. |
| Argument matches 0 sessions | Show the list and ask the user to pick. |
| Argument matches multiple sessions | List the matches with previews; ask which. |
| Extracted session has 0 real turns (only queue/hook events) | Say so plainly; don't fabricate a summary. |
| `.claude-session-rescue/<file>.md` already exists with same name | Append `-1`, `-2` suffix. |
| User invokes the skill a second time after a successful rescue | Refuse per the "one rescue per conversation" rule. |
| User's session is in a language not covered by reference table | Translate the section headers naturally. The principle (front-loaded actionable context, copy-paste continuation prompt, folded full transcript) is language-agnostic. |

---

## Why the design looks like this

A few non-obvious choices worth understanding before changing anything:

- **Orphan detection uses substring match on basename.** Catches both "project moved" and worktree subdirs. Worktrees can be useful to recall too.
- **Old cwd comes from inside the conversation file, not from reversing the dir name.** Reversing `-` back to `/` mishandles real `-` characters — reading the file's own record is ground truth.
- **Migration does global string replacement of the old folder path, not just the cwd field.** When a project moves, every file reference inside the conversation (tool calls, `file_path` values, even paths casually mentioned in messages) becomes a dead link. Doing a global replace makes those files clickable again. The replacement is safe because absolute paths don't collide with regular text.
- **Turn labels in the session history file are colored emoji + bold (🟩 user, 🟧 Claude), not `### headers` and not HTML colored spans.** Original messages often contain their own `##`/`###` headers — wrapping turns in `### header` collides and breaks outline view. Plain bold blends with all the other bold text in messages. HTML colored `<span style="color:...">` gets sanitized in GitHub, Claude Code's preview, and many other previews — colors silently disappear. Emoji squares carry color in the glyph itself and render reliably everywhere.
- **No `<!-- HTML comments -->` in output files.** Some preview engines (Claude Code's preview included) render HTML comments as literal visible text instead of hiding them. Metadata (source path, generation date) goes as italic text at the top instead — visible but visually quiet.
- **No `[label](file:///path)` markdown links for local files.** Many viewers block or strip `file://` for security — the result is a "fake clickable" link that looks active but does nothing. Plain code-formatted absolute paths are honest: universally selectable/copyable, and editors like VS Code and Cursor support Cmd+click on them anyway.
- **Verify every path-like reference inside the transcript.** Original messages often say "I wrote X to `path/Y`" — but Y may have moved, been renamed, or never been created. Without verification, future readers trust dead references. `extract.py --verify-paths` walks every path mention, checks existence, and annotates wrong ones with the actual location (or "not found"). Pay the cost upfront so the file stays trustworthy long after.
- **Detect forked sessions.** A "logical conversation" sometimes lives in multiple jsonl files: a session gets interrupted at a key moment, Claude Code captures the interrupt in one file while continuing in another. The user perceives it as one conversation but sees two file entries. `list_sessions.py` detects this by fingerprinting the first 10 turns — sessions sharing a prefix get marked as forks, with the longest one designated canonical. **Don't hide forks** (each may have unique divergent content), but make the relationship visible so the user knows recalling both is mostly redundant.
- **Confirm explicitly when the user picks a non-canonical fork.** Showing the fork annotation in the listing isn't enough — users skim. Before loading a `fork_of: ...` session, Phase 3a fires an `AskUserQuestion` that surfaces the relationship and offers to switch to the canonical version. One extra confirmation prevents recalling a 99%-redundant session.
- **Migration archives, doesn't delete.** Users move folders on a whim. A one-step recovery (`.trash-` rename) costs nothing and prevents data loss when the heuristic was wrong.
- **Session history file puts the full transcript inside a folded `<details>` block.** A future Claude reading the file should land on actionable info first, not paragraphs of historical chat.
- **No "how deep" mode picker.** Both summary and session history file are cheap to produce. Forcing a choice costs the user attention for no real benefit.
- **Summary language matches source.** Re-reading Chinese work in English-translated form makes you translate back — defeats the purpose.
- **Closing line surfaces affordances + last topic.** Without this hook, the user lands on "what now?" — staring at a wall.

---

## Collaborative protocol

1. **Plain language always.** Every narration, every question, every option must read naturally to a non-technical user. Translate jargon. See "How to talk to the user" above.
2. **Confirm before migrating** — show what moves where, allow cancel.
3. **Archive, don't delete** — orphan dirs get `.trash-` prefix.
4. **One context-loading rescue per conversation.** No exceptions.
5. **Match the source language** — both summary and session history file labels.
6. **Closing line is mandatory** — affordances + last-topic hook, in source language.
7. **Read-only by default** — only writes are `.claude-session-rescue/` files and `.trash-` renames.
8. **Cite timestamps** when claiming a decision from the old conversation, so the user can grep the source.
