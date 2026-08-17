#!/usr/bin/env python3
"""Strip machine-specific UI state from a ComfyUI workflow before committing.

Usage:
    python tools/sanitize_workflow.py workflows/*.json
    python tools/sanitize_workflow.py --check workflows/*.json   # report only, exit 1 if dirty

Some nodes cache the last run's results in their serialized widget values. The worst
offender is VideoHelperSuite's VHS_VideoCombine, which stores a `videopreview` block
containing a `fullpath` to the output file. Committing that leaks a home directory and
pins the graph to one machine. It is pure UI state and the node rebuilds it on the next
run, so removing it costs nothing.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Keys whose values are paths or run-specific results, safe to drop wherever they appear.
DROP_KEYS = {"fullpath", "videopreview", "videopreviewtmp", "audiopreview", "previewaudio"}

ABSOLUTE_PATH = re.compile(r"(?:[A-Za-z]:[\\/]|/(?:home|Users|mnt|media)/)")


def scrub(value, trail: str, removed: list[str]):
    """Recursively drop offending keys. Returns the cleaned value."""
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k.lower() in DROP_KEYS:
                removed.append(f"{trail}.{k}")
                continue
            if isinstance(v, str) and ABSOLUTE_PATH.search(v):
                removed.append(f"{trail}.{k} (absolute path)")
                continue
            out[k] = scrub(v, f"{trail}.{k}", removed)
        return out
    if isinstance(value, list):
        return [scrub(v, f"{trail}[{i}]", removed) for i, v in enumerate(value)]
    return value


def sanitize(path: Path, check_only: bool) -> tuple[bool, list[str]]:
    original = path.read_text(encoding="utf-8")
    graph = json.loads(original)
    removed: list[str] = []

    for node in graph.get("nodes", []):
        label = f"node {node.get('id')} ({node.get('type')})"
        if "widgets_values" in node:
            node["widgets_values"] = scrub(node["widgets_values"], label, removed)

    if not removed:
        return False, []

    if not check_only:
        # Match ComfyUI's own formatting closely enough to keep diffs readable.
        path.write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return True, removed


def main(argv: list[str]) -> int:
    check_only = "--check" in argv
    args = [a for a in argv if a != "--check"]
    root = Path(__file__).resolve().parent.parent
    paths = [Path(a) for a in args] or sorted((root / "workflows").glob("*.json"))

    if not paths:
        print("no workflows to sanitize")
        return 0

    dirty = 0
    for path in paths:
        if not path.exists():
            print(f"FAIL {path}: no such file")
            dirty += 1
            continue
        changed, removed = sanitize(path, check_only)
        if changed:
            dirty += 1
            print(f"{'DIRTY' if check_only else 'CLEANED'} {path}")
            for r in removed:
                print(f"       dropped: {r}")
        else:
            print(f"ok      {path}")

    if check_only and dirty:
        print("\nRun without --check to clean these.")
    return 1 if (check_only and dirty) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
