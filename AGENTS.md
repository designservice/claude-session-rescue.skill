# Claude Session Rescue

Use `SKILL.md` in this directory as the workflow spec when the user wants to recover Claude Code sessions stranded by a project folder move/rename, list past conversations, or load one into a new session as continuation context.

Capability mapping (skill uses these tool names — substitute your platform's equivalents):

- `Read` → file read tool
- `Write` → file write/create tool
- `Edit` → file edit / patch tool (optional; skill mostly writes new files)
- `Bash` → shell command execution
- `Glob` / `Grep` → file search (optional)
- `AskUserQuestion` → ask the user a multiple-choice question in chat
- `Agent` → not used by this skill

All file-level work happens in `scripts/*.py` (standalone Python, stdlib only). The skill body in `SKILL.md` describes when to invoke each script and how to compose their output. No state is persisted outside `<project-root>/.claude-session-rescue/` (output files) and `~/.claude/projects/.trash-*` (archived orphan dirs).

Output format spec lives in `references/session_history_format.md` — read that before generating a session history markdown file.

This skill never sends data anywhere external. It operates entirely on local jsonl files under `~/.claude/projects/`.
