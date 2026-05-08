# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Batch contract validator (OMN-9769, parent OMN-9757).

Phase 3, Task 12 — sweeps a directory tree of contract YAML files,
applies EnumValidatorMode to each file via validate_contract_file, and
returns a ModelBatchValidationSummary aggregating counts + per-file
reports.

Only files named ``contract.yaml`` are processed; all other filenames
are ignored.  Walks the tree recursively so deeply nested node
directories are covered in a single call.
"""

from __future__ import annotations

from pathlib import Path

from omnibase_core.enums.enum_validator_mode import EnumValidatorMode
from omnibase_core.models.contracts.model_batch_validation_summary import (
    ModelBatchValidationSummary,
)
from omnibase_core.models.contracts.model_corpus_validation_report import (
    ModelCorpusValidationReport,
)
from omnibase_core.normalization.contract_validator import validate_contract_file


def run_batch_validation(
    root: Path,
    mode: EnumValidatorMode = EnumValidatorMode.STRICT,
) -> ModelBatchValidationSummary:
    """Walk *root* recursively and validate every ``contract.yaml`` found.

    Args:
        root: Directory to scan.  Non-existent or non-directory paths
            produce a summary with zero counts.
        mode: Validation mode applied to each file.  Defaults to STRICT.

    Returns:
        :class:`ModelBatchValidationSummary` with per-file reports and
        aggregated pass/fail counts.
    """
    if not root.is_dir():
        return ModelBatchValidationSummary(
            total=0,
            passed=0,
            failed=0,
            mode=mode,
            reports=[],
        )

    reports: list[ModelCorpusValidationReport] = []
    for contract_path in sorted(root.rglob("contract.yaml")):
        report = validate_contract_file(contract_path, mode=mode)
        reports.append(report)

    passed = sum(1 for r in reports if r.passed)
    failed = len(reports) - passed

    return ModelBatchValidationSummary(
        total=len(reports),
        passed=passed,
        failed=failed,
        mode=mode,
        reports=reports,
    )


__all__ = ["ModelBatchValidationSummary", "run_batch_validation"]
