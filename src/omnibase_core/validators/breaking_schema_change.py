# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Breaking-schema-change validator (OMN-12621).

Enforces that any **breaking** topic-schema delta is accompanied by an adjacent
:class:`ModelTopicMigrationContract`. This is the enforcement half of the
topic-migration machinery (Rule #5: enforcement, not detection) — wired as a
pre-commit hook and a CI gate in the same change.

Inputs
------
Topic-schema declaration files named ``*.topic-schema.yaml``. Each declares the
current topic↔schema binding plus the immediately-preceding baseline::

    # payments.topic-schema.yaml
    current:
      topic: onex.evt.payments.payment-captured.v2
      event_name: PAYMENT_CAPTURED
      schema_version: {major: 2, minor: 0, patch: 0}
    baseline:
      topic: onex.evt.payments.payment-captured.v1
      event_name: PAYMENT_CAPTURED
      schema_version: {major: 1, minor: 0, patch: 0}

The validator diffs ``baseline`` against ``current`` via
:func:`detect_breaking_delta`. On a breaking delta (``major_bump`` or
``namespace_rename``) it requires an adjacent ``*.migration.yaml`` that parses
as a :class:`ModelTopicMigrationContract` whose ``old_binding`` / ``new_binding``
match the baseline / current bindings. The migration contract is fingerprinted
with :func:`compute_contract_fingerprint` to prove it is well-formed.

Usage::

    python -m omnibase_core.validators.breaking_schema_change src/

Suppression::

    Add  # breaking-schema-ok: <reason>  on a line of the declaration's
    `current.topic` value to silence a finding (rare; prefer authoring the
    migration contract).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml  # ONEX_EXCLUDE: manual_yaml - validator reads adjacent topic-schema/migration YAML

from omnibase_core.contracts.contract_hash_registry import (
    compute_contract_fingerprint,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.contracts.model_topic_migration_contract import (
    ModelTopicMigrationContract,
)
from omnibase_core.models.contracts.model_topic_schema_binding import (
    ModelTopicSchemaBinding,
    detect_breaking_delta,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_breaking_schema_finding import (
    ModelBreakingSchemaFinding,
)

SUPPRESSION_MARKER = "breaking-schema-ok:"

TOPIC_SCHEMA_SUFFIX = ".topic-schema.yaml"
MIGRATION_SUFFIX = ".migration.yaml"

_EXCLUDED_PATH_PARTS: frozenset[str] = frozenset(
    {
        ".venv",
        "__pycache__",
        "build",
        "dist",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "node_modules",
        ".git",
        "archived",
        "archive",
    }
)

_VALIDATOR_NAME = "breaking_schema_change"


def _is_excluded(path: Path) -> bool:
    return any(part in _EXCLUDED_PATH_PARTS for part in path.parts)


def _binding_from_data(data: object) -> ModelTopicSchemaBinding:
    """Build a ModelTopicSchemaBinding from a parsed YAML mapping."""
    if not isinstance(data, dict):
        raise ModelOnexError(
            message="topic-schema binding section must be a mapping",
            error_code=EnumCoreErrorCode.INVALID_INPUT,
        )
    return ModelTopicSchemaBinding.model_validate(data)


def _load_migration_contracts(directory: Path) -> list[ModelTopicMigrationContract]:
    """Load every *.migration.yaml in a directory as a migration contract."""
    contracts: list[ModelTopicMigrationContract] = []
    for mig_path in sorted(directory.glob(f"*{MIGRATION_SUFFIX}")):
        # ONEX_EXCLUDE: manual_yaml - validator reads adjacent migration contract YAML
        raw = yaml.safe_load(mig_path.read_text(encoding="utf-8"))
        contracts.append(ModelTopicMigrationContract.model_validate(raw))
    return contracts


def _migration_covers(
    contract: ModelTopicMigrationContract,
    baseline: ModelTopicSchemaBinding,
    current: ModelTopicSchemaBinding,
) -> bool:
    """True if a migration contract covers this baseline→current transition."""
    return (
        contract.old_binding.topic == baseline.topic
        and contract.old_binding.schema_version == baseline.schema_version
        and contract.new_binding.topic == current.topic
        and contract.new_binding.schema_version == current.schema_version
    )


def validate_file(path: Path) -> list[ModelBreakingSchemaFinding]:
    """Validate one *.topic-schema.yaml declaration; return findings."""
    if _is_excluded(path):
        return []
    text = path.read_text(encoding="utf-8")
    # ONEX_EXCLUDE: manual_yaml - validator reads topic-schema declaration YAML
    data = yaml.safe_load(text)
    if not isinstance(data, dict) or "current" not in data or "baseline" not in data:
        raise ModelOnexError(
            message=(
                f"{path}: topic-schema declaration must contain 'current' and "
                "'baseline' mappings"
            ),
            error_code=EnumCoreErrorCode.INVALID_INPUT,
        )

    current = _binding_from_data(data["current"])
    baseline = _binding_from_data(data["baseline"])

    delta = detect_breaking_delta(baseline, current)
    if not delta.is_breaking:
        return []

    # Suppression: marker on the current.topic line.
    for line in text.splitlines():
        if current.topic in line and SUPPRESSION_MARKER in line:
            return []

    migrations = _load_migration_contracts(path.parent)
    for contract in migrations:
        if _migration_covers(contract, baseline, current):
            # Fingerprint proves the migration contract is well-formed/loadable.
            compute_contract_fingerprint(contract)
            return []

    return [
        ModelBreakingSchemaFinding(
            path=path,
            rule="missing_topic_migration_contract",
            delta=delta.value,
            message=(
                f"breaking topic-schema delta ({delta.value}) "
                f"{baseline.topic} -> {current.topic} has no adjacent "
                f"*{MIGRATION_SUFFIX} ModelTopicMigrationContract covering it"
            ),
        )
    ]


def validate_paths(paths: list[Path]) -> list[ModelBreakingSchemaFinding]:
    """Validate every *.topic-schema.yaml under the given paths."""
    findings: list[ModelBreakingSchemaFinding] = []
    for path in paths:
        if path.is_file() and path.name.endswith(TOPIC_SCHEMA_SUFFIX):
            findings.extend(validate_file(path))
        elif path.is_dir():
            for ts_file in sorted(path.rglob(f"*{TOPIC_SCHEMA_SUFFIX}")):
                if not _is_excluded(ts_file):
                    findings.extend(validate_file(ts_file))
    return findings


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the breaking-schema-change validator."""
    parser = argparse.ArgumentParser(
        description="Breaking-schema-change validator (OMN-12621).",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path("src")],
        help="Files or directories to scan for *.topic-schema.yaml declarations.",
    )
    args = parser.parse_args(argv)

    findings = validate_paths(args.paths)

    if not findings:
        return 0

    sys.stderr.write(f"{_VALIDATOR_NAME}: {len(findings)} finding(s):\n")
    for f in findings:
        sys.stderr.write(f"  {f.format()}\n")
    sys.stderr.write(
        "\nA breaking topic-schema delta requires an adjacent "
        f"*{MIGRATION_SUFFIX} ModelTopicMigrationContract.\n"
        "Suppress an individual line with:  # breaking-schema-ok: <reason>\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: CLI entry point requires SystemExit
