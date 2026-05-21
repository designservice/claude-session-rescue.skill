#!/usr/bin/env python3
"""Migrate one orphan encoded dir into the current project's encoded dir.

For each jsonl in the orphan dir:
- Copy to the current project's encoded dir (skip if target exists)
- Rewrite every `"cwd":"<old>"` occurrence in the copy to the new path

After all jsonl are processed, archive the orphan dir with a `.trash-` prefix
(rename, NOT delete — user can restore).

Usage:
    migrate.py --orphan <encoded_dir> --old-cwd <path> --new-cwd <path>

Output: JSON summary { migrated: [...], skipped: [...], archived_as: "..." }
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path


def encoded_name(path: str) -> str:
    return path.replace("/", "-")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--orphan", required=True, help="orphan encoded dir")
    parser.add_argument("--old-cwd", required=True, help="old project path (read from jsonl)")
    parser.add_argument("--new-cwd", required=True, help="new project path (current cwd)")
    args = parser.parse_args()

    orphan = Path(args.orphan)
    old_cwd = args.old_cwd
    new_cwd = args.new_cwd

    if not orphan.is_dir():
        print(json.dumps({"error": "orphan_not_a_dir", "path": str(orphan)}))
        return 1

    new_encoded = encoded_name(new_cwd)
    new_dir = Path.home() / ".claude" / "projects" / new_encoded
    new_dir.mkdir(parents=True, exist_ok=True)

    migrated: list[str] = []
    skipped: list[str] = []

    # We replace EVERY occurrence of old_cwd in the file, not just the cwd
    # field. The reason: tool calls, file_path values, and even text content
    # often reference paths under the old project root. If we only rewrote
    # the cwd field, the conversation would still link to dead paths,
    # making files in the transcript unclickable.
    # We avoid path-collision pitfalls by requiring exact-string match
    # of the old_cwd (callers must pass the absolute path read from the
    # session file itself, not a guessed prefix).

    for jsonl in sorted(orphan.glob("*.jsonl")):
        target = new_dir / jsonl.name
        if target.exists():
            skipped.append(jsonl.name)
            continue
        content = jsonl.read_text(encoding="utf-8")
        content = content.replace(old_cwd, new_cwd)
        target.write_text(content, encoding="utf-8")
        migrated.append(jsonl.name)

    # Also migrate the memory/ subfolder if present. Claude Code keeps
    # project-level memory files there (MEMORY.md, project_concept.md,
    # user_profile.md, etc.) and these are useful long-term context. If
    # we archive the orphan dir without moving memory, the conversation
    # references to memory files become dead links.
    memory_migrated: list[str] = []
    src_memory = orphan / "memory"
    if src_memory.is_dir():
        dst_memory = new_dir / "memory"
        dst_memory.mkdir(exist_ok=True)
        for f in src_memory.iterdir():
            if not f.is_file():
                continue
            tgt = dst_memory / f.name
            if tgt.exists():
                continue  # don't overwrite existing memory in new project
            tgt.write_bytes(f.read_bytes())
            memory_migrated.append(f.name)

    # Archive the orphan dir (don't delete — user can restore)
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    archived_as = orphan.parent / f".trash-{orphan.name}-{ts}"
    orphan.rename(archived_as)

    print(json.dumps({
        "migrated": migrated,
        "skipped": skipped,
        "memory_migrated": memory_migrated,
        "archived_as": str(archived_as),
        "target_dir": str(new_dir),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
