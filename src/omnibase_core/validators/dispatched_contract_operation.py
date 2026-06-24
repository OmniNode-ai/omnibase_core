# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Require ``handlers[0].operation`` on every dispatched node contract (OMN-13324).

Enforcement Map F8 — verified plan UWP-18. The dispatch-envelope unwrap path
(``node_dod_verify`` ``test_dispatch_envelope_unwrap.py`` and the dispatch engine
generally) resolves the primary handler's operation from
``handler_routing.handlers[0].operation``. A dispatched contract that omits it
surfaces as ``handlers[0].operation is missing`` and the dispatch never resolves
an operation to route on.

Scope vs. the operation_match guard (OMN-13530)
-----------------------------------------------
``operation_match_requires_operation`` enforces ``operation`` on *every* handler
entry whose ``routing_strategy`` is not ``payload_type_match`` — it EXEMPTS
``payload_type_match`` because that strategy routes by ``event_model`` at the
runtime-routing layer.

This gate is narrower-but-orthogonal: it asserts that the FIRST handler of any
dispatchable contract (any contract with a non-empty
``handler_routing.handlers`` list) declares a non-empty ``operation`` —
**regardless of routing_strategy**. The dispatch-envelope unwrap reads
``handlers[0].operation`` to label the dispatch, independent of how the runtime
later resolves which handler runs. A ``payload_type_match`` contract that is a
dispatch target still needs ``handlers[0].operation`` for the unwrap to resolve.

The two gates are complementary: OMN-13530 covers all entries of operation-routed
contracts; this one covers ``handlers[0]`` of *every* dispatchable contract.

Wire it as a pre-commit hook AND a required CI status check in every repo that
carries ONEX node contracts so the dispatch-unwrap regression can never re-land
silently.

Usage::

    python -m omnibase_core.validators.dispatched_contract_operation src/

When pre-commit supplies staged filenames, only ``contract.yaml`` files among
them are scanned. When no paths are supplied, ``src/`` is scanned recursively.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path

import yaml  # ONEX_EXCLUDE: manual_yaml - validator reads adjacent contract.yaml files

from omnibase_core.models.validation.model_dispatched_contract_operation_finding import (
    ModelDispatchedContractOperationFinding,
)

DEFAULT_SCAN_ROOT = Path("src")
CONTRACT_FILENAME = "contract.yaml"


def validate_paths(
    paths: Sequence[Path],
) -> list[ModelDispatchedContractOperationFinding]:
    """Validate the contract.yaml files reachable from the provided paths."""
    findings: list[ModelDispatchedContractOperationFinding] = []
    for path in _iter_contract_files(paths):
        finding = validate_file(path)
        if finding is not None:
            findings.append(finding)
    return findings


def validate_file(path: Path) -> ModelDispatchedContractOperationFinding | None:
    """Validate one contract.yaml: dispatched contract must declare handlers[0].operation.

    Returns a finding when the contract declares a non-empty
    ``handler_routing.handlers`` list (i.e. it is a dispatch target) but its first
    handler lacks a non-empty ``operation`` field. Returns ``None`` otherwise.
    """
    try:
        # ONEX_EXCLUDE: manual_yaml - reading adjacent node contract for validation
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError):
        # YAML/encoding validity is a separate contract-linter concern; this gate
        # only asserts handlers[0].operation on parseable routing blocks.
        return None

    if not isinstance(data, dict):
        return None

    routing = data.get("handler_routing")
    if not isinstance(routing, dict):
        return None

    handlers = routing.get("handlers")
    # A contract with no handlers list is not a dispatch target — out of scope.
    if not isinstance(handlers, list) or not handlers:
        return None

    first = handlers[0]
    if not isinstance(first, dict):
        # A malformed first entry is a separate structural concern; the operation
        # gate only asserts on dict-shaped handler entries.
        return None

    operation = first.get("operation")
    if isinstance(operation, str) and operation.strip():
        return None

    strategy = routing.get("routing_strategy", "")
    strategy = strategy if isinstance(strategy, str) else ""
    return ModelDispatchedContractOperationFinding(
        path=path,
        handler_name=_handler_name(first),
        routing_strategy=strategy,
    )


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
            "Require a non-empty 'operation' field on handlers[0] of every "
            "dispatched node contract (any contract.yaml with a non-empty "
            "handler_routing.handlers list). A missing handlers[0].operation makes "
            "the dispatch-envelope unwrap fail with 'handlers[0].operation is "
            "missing'."
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

    sys.stderr.write("dispatched contract handlers[0].operation guard failed:\n")
    for finding in findings:
        sys.stderr.write(f"  {finding.format()}\n")
    sys.stderr.write(
        "\nEvery dispatched node contract (any contract.yaml with a non-empty "
        "handler_routing.handlers list) must declare a non-empty 'operation' field "
        "on handlers[0]. Without it the dispatch-envelope unwrap fails with "
        "'handlers[0].operation is missing' and the dispatch never resolves an "
        "operation. Add 'operation: <verb>' to the first handler entry.\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: CLI entry point requires SystemExit
