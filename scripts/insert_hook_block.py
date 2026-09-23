#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
#
# OMN-18033: place a propagated hook inside a target's .pre-commit-config.yaml.
#
# scripts/propagate-config.sh used to append the rendered block at end of file.
# That produces an unparseable config in every real target: the block is
# emitted at column 0 while every target indents its repos: entries by two
# spaces, and ten of the twelve declared targets carry top-level keys (ci:,
# fail_fast:, default_stages:) after repos:, so an appended sequence item
# lands outside the list it belongs to.
#
# This helper inserts the block at the end of the repos: list instead, using
# the target's own indentation, and refuses to write a file that does not
# parse afterwards.
#
# Text-level on purpose: a yaml round-trip would reformat the whole target
# file and make the bot's PR unreviewable.

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

_TOP_LEVEL_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*:")
_LIST_ITEM = re.compile(r"^([ ]*)- ")


class _IndentBase(yaml.SafeDumper):
    """Indent sequences under their key, the way every target already writes them.

    yaml.safe_dump emits an indentless sequence — `hooks:` then `- id:` at the
    same column. Every .pre-commit-config.yaml in the fleet indents it, and
    omninode_infra's yamllint fails the indentless form outright (`wrong
    indentation: expected 8 but found 6`).
    """

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        return super().increase_indent(flow, False)


def _literal_str(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
    """Emit any multi-line value as a literal block scalar.

    A hook `description` is a folded multi-line string. yamlfmt re-folds a
    quoted multi-line scalar and injects its own `#magic___^_^___line` marker
    into the value, which onex_change_control's yamlfmt contamination gate
    (OMN-15479) refuses outright — correctly, since the marker lands inside
    committed content. A literal block scalar is not re-folded.
    """
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


class _IndentedDumper(_IndentBase):
    """Indented, preferring literal block scalars for multi-line values."""


class _PlainDumper(_IndentBase):
    """Indented, with PyYAML's default scalar styles — the fallback."""


# add_representer copies the map onto the class it is called on, so _PlainDumper
# keeps the default string representer.
_IndentedDumper.add_representer(str, _literal_str)


def render_block(hook: dict[str, object], pin: str | None) -> str:
    """Render the hook as a `- repo: local` block, optionally pinning its dependency.

    `pin` is a PEP 508 requirement (e.g. "omnibase-core @ git+https://...@<sha>").
    A propagated hook runs in an isolated pre-commit environment, so a hook that
    imports omnibase_core has to carry the dependency with it: without one the
    target gets `ModuleNotFoundError: No module named 'omnibase_core'` on every
    commit. The pin is resolved at propagation time, not stored in the manifest,
    so it names the exact source commit being propagated.
    """
    entry = dict(hook)
    if pin:
        existing = list(entry.get("additional_dependencies") or [])
        if pin not in existing:
            existing.append(pin)
        entry["additional_dependencies"] = existing
    payload = [{"repo": "local", "hooks": [entry]}]
    # Literal block scalars survive the target's formatter, but PyYAML does not
    # round-trip every string through one: a value ending in exactly one newline
    # emits `|` and parses back without it. Content fidelity outranks the style,
    # so the rendering is verified and falls back, and a form that cannot
    # reproduce the declared hook is refused outright rather than propagated.
    for dumper in (_IndentedDumper, _PlainDumper):
        rendered = yaml.dump(payload, Dumper=dumper, sort_keys=False).rstrip()
        if yaml.safe_load(rendered) == payload:
            return str(rendered)
    msg = "no yaml rendering of this hook round-trips to the declared mapping"
    raise ValueError(msg)


def insert(config_text: str, block: str) -> str:
    """Return `config_text` with `block` added to the end of its repos: list."""
    lines = config_text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.startswith("repos:")), None)
    if start is None:
        msg = "target config has no top-level repos: key"
        raise ValueError(msg)

    end = next(
        (i for i in range(start + 1, len(lines)) if _TOP_LEVEL_KEY.match(lines[i])),
        len(lines),
    )

    indent = ""
    for i in range(start + 1, end):
        match = _LIST_ITEM.match(lines[i])
        if match:
            indent = match.group(1)
            break

    # Blank lines and comments immediately before the next top-level key
    # introduce that key, not the repos: list — insert above them.
    while end > start + 1 and (
        lines[end - 1].strip() == "" or lines[end - 1].lstrip().startswith("#")
    ):
        end -= 1

    body = [indent + line if line.strip() else line for line in block.split("\n")]
    return "\n".join(lines[:end] + [""] + body + [""] + lines[end:])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "config",
        type=Path,
        nargs="?",
        help="target .pre-commit-config.yaml (omit with --print-block)",
    )
    parser.add_argument("--hook-json", required=True, help="hook mapping as JSON")
    parser.add_argument(
        "--pin",
        default="",
        help="PEP 508 requirement to add to additional_dependencies",
    )
    parser.add_argument(
        "--print-block",
        action="store_true",
        help="render the block to stdout and exit; the dry-run path uses this so "
        "what it previews is what the live path writes",
    )
    args = parser.parse_args(argv)

    hook = json.loads(args.hook_json)
    hook_id = hook.get("id")
    if not hook_id:
        sys.stderr.write("ERROR: hook mapping has no id\n")
        return 2

    block = render_block(hook, args.pin or None)
    if args.print_block:
        print(block)
        return 0
    if args.config is None:
        sys.stderr.write("ERROR: a config path is required without --print-block\n")
        return 2

    try:
        updated = insert(args.config.read_text(), block)
    except ValueError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 3

    # Fail closed at the point of mutation: never leave a target with a config
    # that pre-commit cannot load.
    try:
        parsed = yaml.safe_load(updated)
    except yaml.YAMLError as exc:
        sys.stderr.write(f"ERROR: insertion produced unparseable yaml: {exc}\n")
        return 4
    ids = [
        h.get("id")
        for repo in (parsed or {}).get("repos") or []
        for h in repo.get("hooks") or []
    ]
    if hook_id not in ids:
        sys.stderr.write(f"ERROR: {hook_id} is not in the repos: list after insertion\n")
        return 5

    args.config.write_text(updated)
    print(f"inserted {hook_id} into {args.config} ({len(ids)} hooks in repos:)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
