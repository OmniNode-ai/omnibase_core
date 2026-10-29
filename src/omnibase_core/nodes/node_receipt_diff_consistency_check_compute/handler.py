# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Thin COMPUTE handler over the receipt diff-consistency validator (OMN-13927)."""

from __future__ import annotations

from pathlib import Path

from omnibase_core.models.nodes.receipt_diff_consistency_check.model_receipt_diff_consistency_check_input import (
    ModelReceiptDiffConsistencyCheckInput,
)
from omnibase_core.models.nodes.receipt_diff_consistency_check.model_receipt_diff_consistency_check_output import (
    ModelReceiptDiffConsistencyCheckOutput,
)
from omnibase_core.models.nodes.receipt_diff_consistency_check.model_receipt_diff_consistency_violation import (
    ModelReceiptDiffConsistencyViolation,
)
from omnibase_core.validation.validator_receipt_diff_consistency import (
    scan_receipt_files_with_diff,
)


class NodeReceiptDiffConsistencyCheckCompute:
    """Check changed receipts' attestations against a name-status diff."""

    def handle(
        self, request: ModelReceiptDiffConsistencyCheckInput
    ) -> ModelReceiptDiffConsistencyCheckOutput:
        findings = scan_receipt_files_with_diff(
            [Path(p) for p in request.receipt_paths], request.name_status
        )
        return ModelReceiptDiffConsistencyCheckOutput(
            violations=[
                ModelReceiptDiffConsistencyViolation(
                    receipt_path=str(finding.receipt_path),
                    attestation=v.attestation,
                    detail=v.detail,
                )
                for finding in findings
                for v in finding.violations
            ]
        )
