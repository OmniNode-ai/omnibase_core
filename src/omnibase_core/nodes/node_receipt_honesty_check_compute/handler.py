# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Thin COMPUTE handler over the receipt-honesty validator (OMN-12791)."""

from __future__ import annotations

from pathlib import Path

from omnibase_core.models.nodes.receipt_honesty_check.model_receipt_honesty_check_input import (
    ModelReceiptHonestyCheckInput,
)
from omnibase_core.models.nodes.receipt_honesty_check.model_receipt_honesty_check_output import (
    ModelReceiptHonestyCheckOutput,
)
from omnibase_core.models.nodes.receipt_honesty_check.model_receipt_honesty_finding import (
    ModelReceiptHonestyFinding,
)
from omnibase_core.models.nodes.receipt_honesty_check.model_receipt_honesty_violation import (
    ModelReceiptHonestyViolation,
)
from omnibase_core.validation.validator_receipt_honesty import (
    scan_receipt_files,
    scan_receipts_directory,
)


class NodeReceiptHonestyCheckCompute:
    """Scan explicit receipt files, or a receipts tree, for honesty violations."""

    def handle(
        self, request: ModelReceiptHonestyCheckInput
    ) -> ModelReceiptHonestyCheckOutput:
        if request.receipt_paths:
            findings = scan_receipt_files([Path(p) for p in request.receipt_paths])
        else:
            findings = scan_receipts_directory(Path(request.receipts_dir))
        return ModelReceiptHonestyCheckOutput(
            findings=[
                ModelReceiptHonestyFinding(
                    receipt_path=str(finding.receipt_path),
                    violations=[
                        ModelReceiptHonestyViolation(rule=v.rule.value, detail=v.detail)
                        for v in finding.violations
                    ],
                )
                for finding in findings
            ]
        )
