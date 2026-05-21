#!/usr/bin/env python3
"""Extract a clean, human-readable conversation stream from a session jsonl.

Filters out:
- queue-operation entries
- attachment / hook events
- tool calls (no associated user-meaningful text)
- skill expansion blobs (text starting with "Base directory for this skill:")
- system reminders, command preambles, "Caveat:" notices

Modes:
- --format markdown (default): one event per block, headers like "### [ts] You/Me"
- --format jsonl: one JSON object per line, with {ts, role, text}
- --format meta: only output session metadata (turn counts, file paths touched)

Optional:
- --tail N: only include the last N user/assistant turn pairs (2N events)
- --include-empty: keep events with no text (default: drop them)

Usage:
    extract.py <path-to-session.jsonl> [--format markdown|jsonl|meta] [--tail N]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

NOISE_PREFIXES = (
    "Base directory for this skill:",
    "<command-",
    "<system-reminder>",
    "Caveat: ",
    # Local command markers — these appear when the user runs a CLI tool that
    # echoes its output back into the session as a "user" turn. They're never
    # actual user input.
    "<local-command-caveat>",
    "<local-command-stdout>",
    "<local-command-stderr>",
)


def extract_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                chunks.append(item.get("text", ""))
        return "\n".join(chunks)
    return ""


def is_noise(text: str) -> bool:
    text = text.lstrip()
    return any(text.startswith(p) for p in NOISE_PREFIXES)


def short_ts(ts: str) -> str:
    """Trim ISO timestamp to second precision."""
    if not ts:
        return ""
    # 2026-04-22T15:44:39.093Z -> 2026-04-22T15:44:39
    if "." in ts:
        return ts.split(".", 1)[0]
    if "Z" in ts:
        return ts.rstrip("Z")
    return ts


def collect_turns(jsonl_path: Path, include_empty: bool) -> tuple[list[dict], list[str]]:
    """Return (turns, files_touched). Each turn = {ts, role, text}."""
    turns: list[dict] = []
    files: set[str] = set()

    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue

            # Collect any file paths referenced (from tool calls etc.)
            for key in ("file_path", "filePath"):
                v = row.get(key)
                if isinstance(v, str) and v:
                    files.add(v)
            # Also dig into tool_use blocks
            msg = row.get("message")
            if isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, list):
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        for key in ("file_path", "filePath"):
                            v = (item.get("input") or {}).get(key) if isinstance(item.get("input"), dict) else None
                            if isinstance(v, str) and v:
                                files.add(v)

            row_type = row.get("type")
            if row_type not in ("user", "assistant"):
                continue

            content = (msg or {}).get("content") if isinstance(msg, dict) else None
            text = extract_text(content)
            if not include_empty and (not text or is_noise(text)):
                continue

            turns.append({
                "ts": short_ts(row.get("timestamp", "")),
                "role": row_type,
                "text": text,
            })

    return turns, sorted(files)


def detect_language(turns: list[dict]) -> str:
    """Return 'zh' if dominant user-message language is Chinese, else 'en'.

    Counts CJK chars vs ASCII letters in user messages. CJK fraction > 0.2
    triggers Chinese labels — threshold is low because mixed bilingual users
    benefit from Chinese labels when they're clearly comfortable in Chinese.
    """
    cjk = 0
    latin = 0
    for t in turns:
        if t["role"] != "user":
            continue
        for ch in t["text"]:
            if "一" <= ch <= "鿿":
                cjk += 1
            elif ch.isascii() and ch.isalpha():
                latin += 1
    total = cjk + latin
    if total == 0:
        return "en"
    return "zh" if cjk / total > 0.2 else "en"


# Turn-label visual markers. Using colored emoji squares instead of inline
# HTML style/color spans because many markdown previewers (GitHub, Claude
# Code's preview, some editors) sanitize out style attributes and the colors
# fail to render. Emoji squares carry their color natively in every viewer.
#   - User: 🟩 green square (cool, complements Claude orange)
#   - Claude: 🟧 orange square (matches Claude brand color)
USER_MARK = "🟩"
ASST_MARK = "🟧"


def render_markdown(turns: list[dict], lang: str | None = None) -> str:
    """Render turns as a human-readable markdown conversation.

    Each turn is separated by `---` so the eye can rest. Speaker labels use
    inline HTML `<span style="color:...">` plus `<strong>` so they stand
    out from any bold text in the message content. Timestamps use `<sub>`
    so they read as secondary metadata.

    Labels are `你 / Claude` for Chinese, `You / Claude` for English. The
    assistant is always "Claude" (not "Me") — the reader of this export is
    in a *new* session with a *different* Claude instance.

    **Why emoji + bold (not headers, not bold-only, not HTML colors):**
    Markdown headers collide with internal `##`/`###` Claude uses in long
    answers (breaks outline). Plain bold blends into other bold text in
    messages. Inline HTML `<span style="color:...">` gets sanitized by
    GitHub, Claude Code's preview, and many editors — the color silently
    disappears. Colored emoji squares carry their color in the glyph itself,
    so they render reliably everywhere: terminals, GitHub, Obsidian, VS
    Code/Cursor preview, Claude Code, etc.

    Original markdown inside each turn (tables, code blocks, lists, bold,
    headers etc.) is preserved verbatim.
    """
    if lang is None:
        lang = detect_language(turns)
    user_label = "你" if lang == "zh" else "You"
    asst_label = "Claude"

    def fmt_header(role: str, ts: str) -> str:
        mark = USER_MARK if role == "user" else ASST_MARK
        label = user_label if role == "user" else asst_label
        head = f"{mark} **{label}**"
        if ts:
            return f"{head} · {ts}"
        return head

    lines = ["---", ""]
    for t in turns:
        ts = t["ts"].replace("T", " ") if t["ts"] else ""
        lines.append(fmt_header(t["role"], ts))
        lines.append("")
        lines.append(t["text"])
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_jsonl(turns: list[dict]) -> str:
    return "\n".join(json.dumps(t, ensure_ascii=False) for t in turns) + "\n"


# File extensions that count as "path-like" for verification. Add more if your
# project uses unusual extensions (Godot .gd, Unreal .uproject, etc.).
PATH_EXTS = (
    'md', 'txt', 'gd', 'cs', 'cpp', 'h', 'rs', 'py', 'js', 'ts', 'tsx', 'jsx',
    'json', 'toml', 'yaml', 'yml', 'go', 'java', 'rb', 'swift', 'kt',
)

_PATH_RE = re.compile(
    r'`([~/][^`\s]+\.(?:' + '|'.join(PATH_EXTS) + r'))`'
    r'|`([\w.][\w./-]*/[\w./-]+\.(?:' + '|'.join(PATH_EXTS) + r'))`'
    r'|(?<![/\w.])(~/[\w./-]+\.(?:' + '|'.join(PATH_EXTS) + r'))(?![/\w])'
    r'|(?<![/\w.])(/[A-Z][\w./-]+\.(?:' + '|'.join(PATH_EXTS) + r'))(?![/\w])'
    r'|(?<![/\w.])([.\w][\w-]*/[\w./-]+\.(?:' + '|'.join(PATH_EXTS) + r'))(?![/\w])'
)


def _resolve_path(p: str, project_root: Path) -> Path:
    if p.startswith('~/'):
        return Path.home() / p[2:]
    if p.startswith('/'):
        return Path(p)
    return project_root / p


def _find_in_project(basename: str, project_root: Path) -> list[Path]:
    """Search project for files matching `basename`. Skip directories that
    conventionally hold non-canonical files:

    - Archives we created: `.trash-*`
    - Git worktrees: `/worktrees/`
    - Version control internals: `/.git/`
    - Package install dirs: `/node_modules/`
    - Our own output: `/.claude-session-rescue/`
    - **Template / example / boilerplate dirs**: when a user's session
      references `foo.md`, they almost never mean a sample/template/example
      copy living in `templates/`, `examples/`, etc. — those are reference
      material, not the real working file. Excluding them dramatically
      reduces false-positive "ambiguous" results.

    The list of skipped path fragments is conservative — if a project
    legitimately keeps its real content inside one of these dirs (rare),
    the user can rename or pass paths explicitly.
    """
    SKIP_FRAGMENTS = (
        '.trash-',
        '/worktrees/',
        '/.git/',
        '/node_modules/',
        '/.claude-session-rescue/',
        # Template / sample / boilerplate dirs:
        '/templates/', '/template/',
        '/examples/', '/example/',
        '/samples/', '/sample/',
        '/boilerplate/', '/skeleton/', '/scaffold/',
    )
    matches = []
    try:
        for cand in project_root.rglob(basename):
            s = str(cand)
            if any(skip in s for skip in SKIP_FRAGMENTS):
                continue
            matches.append(cand)
    except OSError:
        pass
    return matches


_HEADER_RE = re.compile(r'^(#{1,6}) (.*)$')


def demote_headers(text: str, levels: int) -> str:
    """Demote every markdown header in `text` by `levels` levels (cap at h6).

    Why: when this transcript gets embedded as a section inside a larger
    document (e.g. as section 7 "Full transcript" of a session history file
    whose own sections are h2), the message content's original `##`/`###`
    headers — which Claude uses to structure long answers — collide with
    the document's outline. Outline / table-of-contents views render them
    as siblings of the document's h2 sections instead of nested under
    the wrapper. Demoting by 2 makes `##` → `####`, `###` → `#####`, so
    they nest properly under any h2 parent.

    h6 is markdown's maximum heading level; anything that would go past h6
    stays at h6 (still renders, just no further hierarchy info).

    `levels=0` is a no-op (returns input unchanged).
    """
    if levels <= 0:
        return text
    out = []
    for line in text.splitlines():
        m = _HEADER_RE.match(line)
        if m:
            new_level = min(len(m.group(1)) + levels, 6)
            out.append('#' * new_level + ' ' + m.group(2))
        else:
            out.append(line)
    return '\n'.join(out) + ('\n' if text.endswith('\n') else '')


_MD_LINK_RE = re.compile(r'\[([^\]\n]+)\]\(([^)\n]+)\)')


def strip_dead_local_links(text: str) -> str:
    """Convert markdown links to local files into plain text BEFORE path
    annotation runs. Why: if we leave `[label](path)` intact, the subsequent
    path-verification step will match the path inside both `[...]` and `(...)`
    separately and inject annotations into both halves, mangling the link
    syntax. Local file links don't render as clickable in most previews
    anyway (`file://` is sanitized by GitHub, Claude Code's preview, browsers)
    — so we lose nothing by demoting them to plain text.

    Strategy:
    - Skip URLs (http://, https://, ftp://, mailto:, etc.) — keep them as links.
    - For local-looking links where label == url: collapse to just the path.
    - For local-looking links where they differ: render as "label (path)".
    """

    def replace(m):
        label, url = m.group(1).strip(), m.group(2).strip()
        # Keep real URLs as proper markdown links
        if re.match(r'^[a-z][a-z0-9+.-]*://', url, re.IGNORECASE):
            return m.group(0)
        # Also keep anchor-only links (#section)
        if url.startswith('#'):
            return m.group(0)
        # Local file reference — strip the link wrapper
        if label == url:
            return label
        return f'{label} ({url})'

    return _MD_LINK_RE.sub(replace, text)


# Slash-command pattern: matches `/skill-name` or `/namespace:skill-name`.
#
# The two boundary assertions intentionally use *different* word classes —
# this asymmetry resolves a real conflict:
#
# - Lookbehind `(?<!\w)`: Python's default `\w` matches CJK characters, so
#   this correctly excludes cases like "治愈/healing" where the `/` is an
#   "or" separator between words. The CJK char before `/` is `\w`, so
#   lookbehind fails. Real slash commands never sit right after a CJK char
#   (no one writes `选择：/foo` without a space; typed boundaries always
#   involve whitespace or punctuation). Also covers paths (`/to/x`) and
#   URLs (`://example.com/foo`) where ASCII word chars precede.
#
# - Lookahead `(?![A-Za-z0-9_./-])`: explicitly ASCII-only, so CJK
#   characters *after* the command (e.g. `/setup-engine还没跑`) don't look
#   like word continuation. If we used `\w` here too, `还` would force
#   regex backtracking and we'd match the wrong prefix `/setup`.
#   `-` is included so hyphenated names like `/setup-engine` aren't
#   truncated; `.` excludes filename-like trailing parts.
#
# Using `\w` on both sides, or ASCII-only on both sides, breaks one of the
# two cases. The asymmetry is correct.
_SLASH_CMD_RE = re.compile(
    r'(?<!\w)/([a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)?)(?![A-Za-z0-9_./-])'
)


def annotate_skills(text: str, project_root: Path) -> tuple[str, dict]:
    """Find every `/skill-name` reference in `text` and verify the skill
    actually exists at one of the known install paths.

    Why this matters: sessions often reference project-specific skills
    (`/start`, `/brainstorm`, etc. for game projects; `/qa`, `/ship` for
    gstack projects). When the file is read in a new context — a different
    project, a future state where the skill has been removed/renamed —
    these references become silent dead links. Same principle as path
    verification: annotate the unknowns so the reader doesn't trust stale
    references.

    Search order:
      1. `<project_root>/.claude/skills/<name>/SKILL.md` (project-local)
      2. `~/.claude/skills/<name>/SKILL.md` (user-global)
      3. `~/.claude/commands/<name>.md` (legacy slash command)
      4. `~/.claude/commands/<namespace>/<basename>.md` (namespaced)
    """
    stats = {"exists": 0, "missing": 0}

    # Built-in commands that aren't files anywhere — don't flag them
    BUILTINS = {
        'help', 'clear', 'resume', 'compact', 'cost', 'release-notes',
        'config', 'login', 'logout', 'status', 'model', 'init',
        'export', 'pr_comments', 'memory', 'review',
    }

    def skill_exists(name: str) -> bool:
        if name in BUILTINS:
            return True
        # Namespaced like 'gsd:autonomous'
        if ':' in name:
            ns, basename = name.split(':', 1)
            candidates = [
                project_root / '.claude' / 'commands' / ns / f'{basename}.md',
                Path.home() / '.claude' / 'commands' / ns / f'{basename}.md',
                project_root / '.claude' / 'skills' / name / 'SKILL.md',
                Path.home() / '.claude' / 'skills' / name / 'SKILL.md',
            ]
        else:
            candidates = [
                project_root / '.claude' / 'skills' / name / 'SKILL.md',
                Path.home() / '.claude' / 'skills' / name / 'SKILL.md',
                project_root / '.claude' / 'commands' / f'{name}.md',
                Path.home() / '.claude' / 'commands' / f'{name}.md',
            ]
        return any(c.exists() for c in candidates)

    def replace(m):
        name = m.group(1)
        full = m.group(0)
        if skill_exists(name):
            stats["exists"] += 1
            return full
        stats["missing"] += 1
        return f'{full} ⚠️ skill 不存在'

    return _SLASH_CMD_RE.sub(replace, text), stats


def annotate_paths(text: str, project_root: Path) -> tuple[str, dict]:
    """Find every path-like reference in `text`, verify it exists at the
    stated location, and annotate (with a ⚠️ marker pointing at the actual
    location) any that don't.

    Callers should run `strip_dead_local_links()` on the text BEFORE this
    function — otherwise paths embedded in `[label](url)` syntax get matched
    twice (once in label, once in url) and the link syntax breaks.

    Why this matters: when a session's transcript mentions a file path
    (especially from Claude saying "I wrote X to /path/Y"), the file may
    have ended up elsewhere — or never been created. Without verification,
    a future reader trusts the stale reference and gets confused. With
    verification + annotation:
      - Correct paths render untouched
      - Wrong paths with a unique match elsewhere get pointed to the real one
      - Wrong paths with multiple candidates get all candidates listed
      - Wrong paths with no match get a "not found" marker

    Returns (annotated_text, stats_dict).
    """
    stats = {"exists": 0, "fixed_unique": 0, "fixed_listed": 0, "missing": 0}

    def replace(m):
        # find which alternation group captured
        path_str = next((g for g in m.groups() if g), None)
        if not path_str:
            return m.group(0)
        full = m.group(0)

        resolved = _resolve_path(path_str, project_root)
        if resolved.exists():
            stats["exists"] += 1
            return full

        basename = Path(path_str).name
        candidates = _find_in_project(basename, project_root)
        if len(candidates) == 1:
            stats["fixed_unique"] += 1
            return f'{full} ⚠️ 实际位于 `{candidates[0]}`'
        if len(candidates) == 0:
            stats["missing"] += 1
            return f'{full} ⚠️ 此文件未找到'
        stats["fixed_listed"] += 1
        cand_list = '; '.join(f'`{c}`' for c in candidates)
        return f'{full} ⚠️ 此路径不存在，候选位置：{cand_list}'

    return _PATH_RE.sub(replace, text), stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", help="path to session jsonl")
    parser.add_argument("--format", choices=("markdown", "jsonl", "meta"), default="markdown")
    parser.add_argument("--tail", type=int, default=0, help="only include last N turns (0 = all)")
    parser.add_argument("--include-empty", action="store_true")
    parser.add_argument("--lang", choices=("auto", "zh", "en"), default="auto",
                        help="label language for markdown output (default: auto-detect from user messages)")
    parser.add_argument("--verify-paths", metavar="PROJECT_ROOT", default=None,
                        help="annotate path-like references against this project root. "
                             "Paths that don't exist get a ⚠️ marker pointing to the actual "
                             "location (if a unique match is found) or 'not found' otherwise.")
    parser.add_argument("--demote", type=int, default=0, metavar="N",
                        help="demote every markdown header in the message content by N "
                             "levels (cap at h6). Use --demote 2 when embedding the output "
                             "under an h2 wrapper so internal headers nest properly.")
    args = parser.parse_args()

    jsonl = Path(args.jsonl)
    if not jsonl.is_file():
        print(f"error: not a file: {jsonl}", file=sys.stderr)
        return 1

    turns, files = collect_turns(jsonl, args.include_empty)

    if args.tail and args.tail > 0:
        turns = turns[-args.tail:]

    if args.format == "meta":
        user_count = sum(1 for t in turns if t["role"] == "user")
        assistant_count = sum(1 for t in turns if t["role"] == "assistant")
        meta = {
            "short_id": jsonl.stem[:8],
            "full_id": jsonl.stem,
            "turn_count": len(turns),
            "user_count": user_count,
            "assistant_count": assistant_count,
            "first_ts": turns[0]["ts"] if turns else None,
            "last_ts": turns[-1]["ts"] if turns else None,
            "files_touched": files,
        }
        print(json.dumps(meta, ensure_ascii=False, indent=2))
    elif args.format == "jsonl":
        sys.stdout.write(render_jsonl(turns))
    else:
        lang = None if args.lang == "auto" else args.lang
        out = render_markdown(turns, lang=lang)
        if args.demote > 0:
            out = demote_headers(out, args.demote)
        if args.verify_paths:
            project_root = Path(args.verify_paths).resolve()
            # Strip dead local-file markdown links BEFORE path annotation so
            # the regex doesn't match paths inside [label](url) twice.
            out = strip_dead_local_links(out)
            out, path_stats = annotate_paths(out, project_root)
            out, skill_stats = annotate_skills(out, project_root)
            print(f"# path verification: {path_stats}", file=sys.stderr)
            print(f"# skill verification: {skill_stats}", file=sys.stderr)
        sys.stdout.write(out)

    return 0


if __name__ == "__main__":
    sys.exit(main())
