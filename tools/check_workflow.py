#!/usr/bin/env python3
"""Validate ComfyUI workflow JSON against the repo conventions.

Usage:
    python tools/check_workflow.py workflows/*.json
    python tools/check_workflow.py          # checks every workflow in the repo

Errors block a commit. Warnings are judgment calls the checker cannot make.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Documentation and plumbing. These carry no role, so they need no title.
EXEMPT_TYPES = {"Note", "MarkdownNote", "Reroute", "PrimitiveNode"}

MAX_TITLE_LEN = 40

# Paths that resolve on exactly one machine.
ABSOLUTE_PATH = re.compile(r"(?:[A-Za-z]:[\\/]|/(?:home|Users|mnt|media)/)")

# Titles that are abbreviations rather than names: POS, K, CKPT, VD.
ABBREVIATION = re.compile(r"^[A-Z0-9_]{1,5}$")

# Sampler-ish nodes whose seed control matters for comparisons.
SEED_NODES = re.compile(r"sampler|noise|seed", re.IGNORECASE)


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def widget_strings(node: dict):
    """Yield every string in a node's widget values, flattening nested lists."""
    stack = [node.get("widgets_values") or []]
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            yield item
        elif isinstance(item, (list, tuple)):
            stack.extend(item)
        elif isinstance(item, dict):
            stack.extend(item.values())


def check(path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        graph = load(path)
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc}"], []

    nodes = graph.get("nodes")
    if nodes is None:
        if isinstance(graph, dict) and any(
            isinstance(v, dict) and "class_type" in v for v in graph.values()
        ):
            return ["API-format graph in workflows/; UI format belongs here"], []
        return ["no 'nodes' array; not a ComfyUI UI-format workflow"], []

    seen: dict[str, int] = {}

    for node in nodes:
        node_id = node.get("id", "?")
        node_type = node.get("type", "?")
        where = f"node {node_id} ({node_type})"
        title = (node.get("title") or "").strip()

        if node_type not in EXEMPT_TYPES:
            if not title:
                errors.append(f"{where}: untitled")
            elif title == node_type:
                errors.append(f"{where}: title is the class name")
            elif ABBREVIATION.match(title):
                errors.append(f"{where}: title '{title}' is an abbreviation")
            elif len(title) > MAX_TITLE_LEN:
                errors.append(
                    f"{where}: title is {len(title)} chars, limit is {MAX_TITLE_LEN}"
                )
            elif not title.isascii():
                errors.append(f"{where}: title '{title}' has non-ASCII characters")

            if title:
                if title in seen:
                    errors.append(
                        f"{where}: title '{title}' already used by node {seen[title]}"
                    )
                else:
                    seen[title] = node_id

        for value in widget_strings(node):
            if ABSOLUTE_PATH.search(value):
                errors.append(f"{where}: absolute path in widget: {value!r}")
            elif value == "randomize" and SEED_NODES.search(node_type):
                warnings.append(
                    f"{where}: control_after_generate is randomize, "
                    "so A/B runs will not match"
                )

    if not any(node.get("type") not in EXEMPT_TYPES for node in nodes):
        errors.append("graph has no functional nodes")

    notes = path.with_suffix(".md")
    if not notes.exists():
        errors.append(f"missing notes file: {notes.name}")

    return errors, warnings


def main(argv: list[str]) -> int:
    root = Path(__file__).resolve().parent.parent
    if argv:
        paths = [Path(a) for a in argv]
    else:
        paths = sorted((root / "workflows").glob("*.json"))

    if not paths:
        print("no workflows to check")
        return 0

    failed = 0
    for path in paths:
        if not path.exists():
            print(f"FAIL {path}: no such file")
            failed += 1
            continue

        errors, warnings = check(path)
        label = "FAIL" if errors else "ok  "
        print(f"{label} {path}")
        for message in errors:
            print(f"       error: {message}")
        for message in warnings:
            print(f"       warn:  {message}")
        if errors:
            failed += 1

    print(f"\n{len(paths) - failed}/{len(paths)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
