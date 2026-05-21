<div align="center">

# Claude Session Rescue

<sub>`claude-session-rescue.skill`</sub>

**Project folder moved? Your conversations follow.**

[中文说明](README.zh-CN.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent-Agnostic](https://img.shields.io/badge/Agent-Agnostic-blueviolet)](https://skills.sh)
[![skills.sh](https://img.shields.io/badge/skills.sh-Compatible-green)](https://skills.sh)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Compatible-cc785c)](https://claude.com/claude-code)
[![Python](https://img.shields.io/badge/Python-3.8+-3776ab)](https://www.python.org)

```bash
npx skills add designservice/claude-session-rescue.skill
```

[Why it exists](#why-it-exists) · [What it does](#what-it-does) · [Install](#install) · [Usage](#usage) · [Output](#output)

</div>

---

## Why It Exists

You renamed a folder, moved a project, or reorganized your directory structure. Now your old Claude Code conversations are nowhere to be found.

They're still on disk — just stranded under the old path. This skill finds them, migrates the files, summarizes where you left off, and gives you a clean markdown handoff to continue in a new session.

Use it when:

- Old conversations disappeared after a project move or rename.
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

<div align="center">

MIT License © designservice

</div>
