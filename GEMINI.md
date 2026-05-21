# Claude Session Rescue

Use `SKILL.md` in this directory as the workflow spec when the user wants to recover Claude Code sessions stranded by a project folder move/rename, list past conversations, or load one into a new session as continuation context.

Tool mapping (the skill uses Claude Code tool names — substitute Gemini CLI equivalents):

- `Read` → file read
- `Write` → file write
- `Bash` → shell execution
- `AskUserQuestion` → multiple-choice prompt to user

This skill runs entirely on local data under `~/.claude/projects/` and writes only to `<project-root>/.claude-session-rescue/`. No network calls.

Output format spec lives in `references/session_history_format.md`.
