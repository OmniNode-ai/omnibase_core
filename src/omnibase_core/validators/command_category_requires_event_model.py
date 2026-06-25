# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Require an ``event_model`` on command-category handler_routing entries (OMN-13028).

A ``handler_routing.handlers[]`` entry tagged ``message_category: command`` names a
typed command payload. The dispatcher resolves that payload type from the entry's
``event_model`` block (``{name, module}``). When a command entry omits
``event_model``, the contract is the exact failure behind OMN-13003 — a command
handler with no event_model — and the node fails closed (or silently degenerates,
attempt_count=0) at runtime. This is ladder layer 1 of the OMN-13003/13005 top-10
failure (Wall of Shame row 14).

This validator is the commit-time enforcement gate: it scans ``contract.yaml``
files and fails if any handler_routing entry with ``message_category: command``
lacks a non-empty ``event_model``. Wire it as a pre-commit hook AND a required CI
status check in every repo that carries ONEX node contracts so the regression can
never re-land silently.

Scope: only entries explicitly tagged ``message_category: command`` are checked.
Entries with category ``event``/``intent``, or no ``message_category`` at all, are
out of scope here — they are governed by other routing guards (e.g. the
operation_match operation-field guard, OMN-13530). The boot-time half of OMN-13028
(auto-wiring raising on a no-op/None-returning injected consumer) is tracked as a
separate follow-up; this module is the commit-time, pure-code deliverable.

Usage::

    python -m omnibase_core.validators.command_category_requires_event_model src/

When pre-commit supplies staged filenames, only ``contract.yaml`` files among them
are scanned. When no paths are supplied, ``src/`` is scanned recursively.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path

import yaml  # ONEX_EXCLUDE: manual_yaml - validator reads adjacent contract.yaml files

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.models.validation.model_command_event_model_finding import (
    ModelCommandEventModelFinding,
)

DEFAULT_SCAN_ROOT = Path("src")
CONTRACT_FILENAME = "contract.yaml"
COMMAND_CATEGORY = EnumMessageCategory.COMMAND.value  # "command"


def validate_paths(paths: Sequence[Path]) -> list[ModelCommandEventModelFinding]:
    """Validate the contract.yaml files reachable from the provided paths."""
    findings: list[ModelCommandEventModelFinding] = []
    for path in _iter_contract_files(paths):
        findings.extend(validate_file(path))
    return findings


def validate_file(path: Path) -> list[ModelCommandEventModelFinding]:
    """Validate one contract.yaml for command entries missing ``event_model``."""
    try:
        # ONEX_EXCLUDE: manual_yaml - reading adjacent node contract for validation
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError):
        # YAML/encoding validity is a separate contract-linter concern; this gate
        # only asserts event_model on parseable command-category routing entries.
        return []

    if not isinstance(data, dict):
        return []

    routing = data.get("handler_routing")
    if not isinstance(routing, dict):
        return []

    handlers = routing.get("handlers")
    if not isinstance(handlers, list):
        return []

    findings: list[ModelCommandEventModelFinding] = []
    for index, entry in enumerate(handlers):
        if not isinstance(entry, dict):
            continue
        if not _is_command_category(entry):
            continue
        if _has_event_model(entry):
            continue
        findings.append(
            ModelCommandEventModelFinding(
                path=path,
                handler_index=index,
                handler_name=_handler_name(entry),
            )
        )
    return findings


def _is_command_category(entry: dict[str, object]) -> bool:
    category = entry.get("message_category")
    if not isinstance(category, str):
        return False
    return category.strip().lower() == COMMAND_CATEGORY


def _has_event_model(entry: dict[str, object]) -> bool:
    event_model = entry.get("event_model")
    if isinstance(event_model, dict):
        # A nested {name, module} block must carry a non-empty name to be real.
        name = event_model.get("name")
        return isinstance(name, str) and bool(name.strip())
    if isinstance(event_model, str):
        return bool(event_model.strip())
    return False


def _handler_name(entry: dict[str, object]) -> str:
    handler = entry.get("handler")
    if isinstance(handler, dict):
        name = handler.get("name")
        if isinstance(name, str) and name:
            return name
    handler_key = entry.get("handler_key")
    if isinstance(handler_key, str) and handler_key:
        return handler_key
    handler_class = entry.get("handler_class")
    if isinstance(handler_class, str) and handler_class:
        return handler_class
    return "<unnamed>"


def _iter_contract_files(paths: Sequence[Path]) -> Iterator[Path]:
    scan_paths = tuple(paths) or (DEFAULT_SCAN_ROOT,)
    for path in scan_paths:
        if path.is_file() and path.name == CONTRACT_FILENAME:
            yield path
        elif path.is_dir():
            yield from sorted(
                candidate
                for candidate in path.rglob(CONTRACT_FILENAME)
                if "__pycache__" not in candidate.parts
            )


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Require a non-empty 'event_model' on every handler_routing entry "
            "tagged message_category: command. A missing event_model is the "
            "OMN-13003 failure — a command handler with no payload model — and "
            "makes the node fail closed (or degenerate) at runtime."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_SCAN_ROOT],
        help="contract.yaml file or directory paths to scan.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    findings = validate_paths(args.paths)
    if not findings:
        return 0

    sys.stderr.write("command-category handler 'event_model' guard failed:\n")
    for finding in findings:
        sys.stderr.write(f"  {finding.format()}\n")
    sys.stderr.write(
        "\nEvery handler_routing entry tagged 'message_category: command' must "
        "declare a non-empty 'event_model' (a nested {name, module} block naming "
        "the command payload model). Without it the dispatcher cannot resolve the "
        "command payload type (OMN-13003), and the node fails closed or degenerates "
        "at runtime. Add the 'event_model:' block alongside the command handler.\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: CLI entry point requires SystemExit
