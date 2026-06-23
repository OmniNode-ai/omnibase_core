# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Require an ``operation`` field on operation_match handler entries (OMN-13530).

RuntimeLocal._validate_routing (omnibase_core.runtime.runtime_local) requires an
``operation`` field on every ``handler_routing.handlers[]`` entry whose
``routing_strategy`` is NOT ``payload_type_match``. ``operation_match`` is the
explicit strategy; an *absent* ``routing_strategy`` falls into the same branch
because the runtime defaults the missing value to the empty string and only the
``payload_type_match`` branch is special-cased.

A handler entry that routes by operation but omits ``operation`` makes the whole
contract fail closed at runtime startup::

    RuntimeLocal: routing validation error: handlers[0].operation is missing
    RuntimeLocal: result=failed

This is the regression that took down the headless automation fleet
(merge_sweep, ci_watch, auto_merge, build_loop, coderabbit_triage,
create_ticket) after omnibase_core 0.46.0 hardened ``_validate_routing``.

This validator is the enforcement gate: it scans ``contract.yaml`` files and
fails if any operation-routed handler entry lacks a non-empty ``operation``. Wire
it as a pre-commit hook AND a required CI status check in every repo that carries
ONEX node contracts so the regression can never re-land silently.

Usage::

    python -m omnibase_core.validators.operation_match_requires_operation src/

When pre-commit supplies staged filenames, only ``contract.yaml`` files among
them are scanned. When no paths are supplied, ``src/`` is scanned recursively.

Note on scope: this gate checks ONLY the ``operation`` field — it intentionally
does NOT assert the presence of the nested ``handler.name`` / ``handler.module``
block (a separate _validate_routing requirement). A handler entry that uses the
legacy ``routing_key`` / ``handler_key`` shape (no nested ``handler:`` block) has
a distinct structural gap that is out of scope here.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path

import yaml  # ONEX_EXCLUDE: manual_yaml - validator reads adjacent contract.yaml files

from omnibase_core.models.validation.model_operation_match_finding import (
    ModelOperationMatchFinding,
)

DEFAULT_SCAN_ROOT = Path("src")
CONTRACT_FILENAME = "contract.yaml"
PAYLOAD_TYPE_MATCH = "payload_type_match"


def validate_paths(paths: Sequence[Path]) -> list[ModelOperationMatchFinding]:
    """Validate the contract.yaml files reachable from the provided paths."""
    findings: list[ModelOperationMatchFinding] = []
    for path in _iter_contract_files(paths):
        findings.extend(validate_file(path))
    return findings


def validate_file(path: Path) -> list[ModelOperationMatchFinding]:
    """Validate one contract.yaml file for operation_match entries missing ``operation``."""
    try:
        # ONEX_EXCLUDE: manual_yaml - reading adjacent node contract for validation
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError):
        # YAML/encoding validity is a separate contract-linter concern; this gate
        # only asserts the operation field on parseable routing blocks.
        return []

    if not isinstance(data, dict):
        return []

    routing = data.get("handler_routing")
    if not isinstance(routing, dict):
        return []

    strategy = routing.get("routing_strategy", "")
    strategy = strategy if isinstance(strategy, str) else ""
    # Mirror RuntimeLocal._validate_routing: only payload_type_match is exempt;
    # every other strategy (operation_match, or an absent/empty one) routes by
    # the operation field.
    if strategy == PAYLOAD_TYPE_MATCH:
        return []

    handlers = routing.get("handlers")
    if not isinstance(handlers, list):
        return []

    findings: list[ModelOperationMatchFinding] = []
    for index, entry in enumerate(handlers):
        if not isinstance(entry, dict):
            continue
        operation = entry.get("operation")
        if isinstance(operation, str) and operation.strip():
            continue
        findings.append(
            ModelOperationMatchFinding(
                path=path,
                handler_index=index,
                strategy=strategy,
                handler_name=_handler_name(entry),
            )
        )
    return findings


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
            "Require a non-empty 'operation' field on every handler_routing entry "
            "whose routing_strategy is operation_match (or absent). A missing "
            "operation makes the contract fail closed at RuntimeLocal startup."
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

    sys.stderr.write("operation_match handler 'operation' field guard failed:\n")
    for finding in findings:
        sys.stderr.write(f"  {finding.format()}\n")
    sys.stderr.write(
        "\nEvery operation_match (or absent-strategy) handler_routing entry must "
        "declare a non-empty 'operation' field. Without it RuntimeLocal fails "
        "closed at startup with 'handlers[i].operation is missing' and the node "
        "never loads. Add 'operation: <verb>' alongside each handler block.\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: CLI entry point requires SystemExit
