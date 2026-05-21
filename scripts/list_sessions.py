#!/usr/bin/env python3
"""List sessions in a Claude Code encoded project dir.

Reads each jsonl, extracts:
- short_id, full_id, started_at, last_activity, turn_count, first_user_message

ALSO detects "fork" relationships. Claude Code sometimes stores a single
logical conversation across multiple jsonl files — e.g., when a message gets
interrupted, the original file captures the interrupt while a parallel file
continues the conversation. Both files share an identical prefix (often
hundreds of turns), then diverge.

Without detecting this, the user sees what looks like several independent
sessions but is actually one conversation in disguise. Recalling each one
separately produces ~99% redundant content.

The detection: for each session, compute a fingerprint over the first K
turns (timestamp + role + content-hash). Sessions sharing a fingerprint are
in the same fork-group. Within a group, find the longest common prefix
across all members (by walking turn-by-turn), designate the longest member
as `canonical`, and annotate each session with `fork_of`, `common_prefix`,
`divergent_turns`.

Output: JSON list to stdout, sorted by started_at descending.

Usage:
    list_sessions.py --dir <encoded_project_dir> [--exclude <session-id>]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

NOISE_PREFIXES = (
    "Base directory for this skill:",
    "<command-",
    "<system-reminder>",
    "Caveat: ",
    "<local-command-caveat>",
    "<local-command-stdout>",
    "<local-command-stderr>",
)

# Number of leading turns used for the fork-group fingerprint. Long enough
# to be specific (rare for two unrelated conversations to share this many
# leading turns), short enough to compute fast.
PREFIX_FINGERPRINT_K = 10


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


def _content_hash(content) -> str:
    s = json.dumps(content, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:10]


def scan_jsonl(path: Path) -> dict:
    """Scan one jsonl, return metadata + all turn fingerprints (for fork
    detection). Turn fingerprints are kept under `_all_turns` (private,
    consumed by the fork-detection pass; stripped from the final output)."""
    short_id = path.stem[:8]
    full_id = path.stem

    first_ts = None
    last_ts = None
    turn_count = 0
    first_user_msg = None
    all_turns: list[tuple[str, str, str]] = []

    try:
        with path.open(encoding="utf-8") as f:
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

                ts = row.get("timestamp")
                if ts:
                    if first_ts is None:
                        first_ts = ts
                    last_ts = ts

                row_type = row.get("type")
                if row_type not in ("user", "assistant"):
                    continue

                message = row.get("message") or {}
                content = message.get("content") if isinstance(message, dict) else None
                text = extract_text(content)
                if not text or is_noise(text):
                    continue

                turn_count += 1
                if row_type == "user" and first_user_msg is None:
                    first_user_msg = text[:200].replace("\n", " ")

                all_turns.append((ts or "", row_type, _content_hash(content)))
    except OSError:
        pass

    return {
        "short_id": short_id,
        "full_id": full_id,
        "started_at": first_ts,
        "last_activity": last_ts,
        "turn_count": turn_count,
        "first_user_message": first_user_msg,
        "path": str(path),
        "_all_turns": all_turns,
    }


def _prefix_fingerprint(turns: list[tuple[str, str, str]]) -> str | None:
    """Hash of the first K turns. None if too short to fingerprint."""
    if len(turns) < PREFIX_FINGERPRINT_K:
        return None
    prefix = json.dumps(turns[:PREFIX_FINGERPRINT_K])
    return hashlib.md5(prefix.encode("utf-8")).hexdigest()[:16]


def detect_forks(sessions: list[dict]) -> None:
    """Mutate sessions: add `fork_of`, `is_canonical`, `common_prefix_turns`,
    `divergent_turns` where applicable.

    Two sessions are in the same fork group iff their first K turns share
    identical (timestamp, role, content-hash) tuples. Within a group, the
    common prefix length is the longest position where all members still
    match turn-by-turn. The session with the most total turns is designated
    canonical; others are forks of it.
    """
    groups: dict[str, list[dict]] = {}
    for s in sessions:
        fp = _prefix_fingerprint(s["_all_turns"])
        if fp:
            groups.setdefault(fp, []).append(s)

    for fp, group in groups.items():
        if len(group) < 2:
            continue
        # Find common prefix length across all members
        turn_lists = [s["_all_turns"] for s in group]
        min_len = min(len(t) for t in turn_lists)
        common = 0
        for i in range(min_len):
            ref = turn_lists[0][i]
            if all(t[i] == ref for t in turn_lists):
                common = i + 1
            else:
                break

        # Designate canonical: the one with most turns (longest record)
        canonical = max(group, key=lambda s: s["turn_count"])
        for s in group:
            s["fork_of"] = canonical["short_id"] if s is not canonical else None
            s["is_canonical"] = (s is canonical)
            s["common_prefix_turns"] = common
            s["divergent_turns"] = max(s["turn_count"] - common, 0)
            # Also record sibling short_ids for cross-reference
            s["fork_siblings"] = [o["short_id"] for o in group if o is not s]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="encoded project dir")
    parser.add_argument("--exclude", default=None, help="full session uuid to exclude")
    args = parser.parse_args()

    project_dir = Path(args.dir)
    if not project_dir.is_dir():
        print(json.dumps({"error": "not_a_dir", "path": str(project_dir)}))
        return 1

    sessions = []
    for jsonl in sorted(project_dir.glob("*.jsonl")):
        if args.exclude and jsonl.stem == args.exclude:
            continue
        sessions.append(scan_jsonl(jsonl))

    detect_forks(sessions)

    # Strip private fields before output
    for s in sessions:
        s.pop("_all_turns", None)

    sessions.sort(key=lambda s: (s["started_at"] or ""), reverse=True)
    print(json.dumps(sessions, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
