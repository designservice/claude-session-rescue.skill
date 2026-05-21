#!/usr/bin/env python3
"""Find orphaned encoded project dirs.

Detects ~/.claude/projects/* directories whose basename matches the current
project's basename but whose encoded path doesn't match the current cwd —
these are leftover from a folder rename/move.

Output: JSON to stdout with:
- current_dir: absolute cwd
- current_encoded: encoded dir for current cwd
- orphans: list of {encoded_dir, old_cwd, jsonl_count}

The old_cwd is read from the jsonl files themselves (more reliable than
reverse-decoding the encoded name, which mishandles real `-` characters).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def encoded_name(path: Path) -> str:
    """Replicate Claude Code's encoding: replace / with -."""
    return str(path).replace("/", "-")


def first_cwd_from_jsonl(jsonl_path: Path) -> str | None:
    """Read the first non-null `cwd` field from a jsonl file."""
    try:
        with jsonl_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict) and row.get("cwd"):
                    return row["cwd"]
    except OSError:
        return None
    return None


def main() -> int:
    current_dir = Path.cwd().resolve()
    current_encoded = encoded_name(current_dir)
    projects_root = Path.home() / ".claude" / "projects"

    if not projects_root.exists():
        print(json.dumps({
            "current_dir": str(current_dir),
            "current_encoded": current_encoded,
            "orphans": [],
            "error": "projects_root_not_found",
        }))
        return 0

    base = current_dir.name
    orphans = []

    for d in projects_root.iterdir():
        if not d.is_dir():
            continue
        name = d.name
        # Skip archived dirs and the current project's own encoded dir
        if name.startswith(".trash-"):
            continue
        if name == current_encoded:
            continue
        # Must contain the basename as a substring (relaxed match — handles
        # cases where the encoded path has prefixes/suffixes around the base)
        if base not in name:
            continue

        jsonls = sorted(d.glob("*.jsonl"))
        if not jsonls:
            continue

        # Pick the first jsonl and read its cwd
        old_cwd = None
        for j in jsonls:
            old_cwd = first_cwd_from_jsonl(j)
            if old_cwd:
                break

        # False-positive guard: if the recorded cwd equals current cwd, it's
        # not really an orphan (e.g., the dir was created after the move)
        if old_cwd == str(current_dir):
            continue

        orphans.append({
            "encoded_dir": str(d),
            "old_cwd": old_cwd,  # may be None if unreadable
            "jsonl_count": len(jsonls),
        })

    print(json.dumps({
        "current_dir": str(current_dir),
        "current_encoded": current_encoded,
        "orphans": orphans,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
