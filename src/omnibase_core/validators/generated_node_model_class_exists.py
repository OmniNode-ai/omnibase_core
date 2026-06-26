# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Enforce contract-declared model classes exist in the generated handler (OMN-13609).

WS-C Phase 1.1 enforcement gate. Ported from the SEA generation pipeline's
``model_types`` check, the authoritative logic lives in the canonical validator
platform — :func:`omnibase_core.validation.validator_contract_linter.validate_model_class_existence`.
This module is the thin pre-commit / CI enforcement wrapper around that platform
authority: it does NOT re-implement the check, it invokes it.

A generated ONEX node directory co-locates ``contract.yaml`` with ``handler.py``.
The contract declares ``input_model`` / ``output_model`` class names; those classes
must be defined as top-level classes in the generated handler. A contract that
references an undefined model class is rejected.

Scope: only ``contract.yaml`` files that have a sibling ``handler.py`` are
checked — the existence of a model class can only be proven against a handler. A
contract-only directory (no co-located handler) is out of scope.

Usage::

    python -m omnibase_core.validators.generated_node_model_class_exists src/

When pre-commit supplies staged filenames, only ``contract.yaml`` files among
them (that have a sibling ``handler.py``) are scanned. When no paths are
supplied, ``src/`` is scanned recursively.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path

import yaml  # ONEX_EXCLUDE: manual_yaml - validator reads adjacent contract.yaml files

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.validation.validator_contract_linter import (
    validate_model_class_existence,
)

DEFAULT_SCAN_ROOT = Path("src")
CONTRACT_FILENAME = "contract.yaml"
HANDLER_FILENAME = "handler.py"


def validate_paths(paths: Sequence[Path]) -> list[ModelValidationIssue]:
    """Validate every generated-node contract reachable from the provided paths."""
    issues: list[ModelValidationIssue] = []
    for contract_path in _iter_generated_node_contracts(paths):
        issues.extend(validate_file(contract_path))
    return issues


def validate_file(contract_path: Path) -> list[ModelValidationIssue]:
    """Validate one generated-node contract against its co-located handler.

    Delegates the check to the canonical platform authority
    (:func:`validate_model_class_existence`). Returns the platform issues for
    declared model classes absent from the handler; empty otherwise.
    """
    handler_path = contract_path.parent / HANDLER_FILENAME
    if not handler_path.is_file():
        return []

    try:
        # ONEX_EXCLUDE: manual_yaml - reading adjacent node contract for validation
        data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError):
        # YAML/encoding validity is the contract-linter's concern; this gate only
        # asserts model-class existence on parseable contracts.
        return []
    if not isinstance(data, dict):
        return []

    try:
        handler_source = handler_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    return validate_model_class_existence(
        data,
        handler_source,
        path=contract_path,
        severity=EnumSeverity.ERROR,
    )


def _iter_generated_node_contracts(paths: Sequence[Path]) -> Iterator[Path]:
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
            "Require that a generated node's contract-declared input_model / "
            "output_model class names exist as top-level classes in the "
            "co-located handler.py. Invokes the canonical validator platform "
            "(validate_model_class_existence)."
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
    issues = validate_paths(args.paths)
    if not issues:
        return 0

    sys.stderr.write("generated-node model-class-existence guard failed:\n")
    for issue in issues:
        location = str(issue.file_path) if issue.file_path else "<unknown>"
        sys.stderr.write(f"  {location}: {issue.message}\n")
    sys.stderr.write(
        "\nEvery generated node's contract-declared input_model / output_model "
        "class name must be defined as a top-level class in the co-located "
        "handler.py. Define the missing class in the handler, or update the "
        "contract to match the handler's class name.\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: CLI entry point requires SystemExit
