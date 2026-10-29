# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Thin COMPUTE handler over the receipt runtime-identity gate (OMN-21520)."""

from __future__ import annotations

from pathlib import Path

from omnibase_core.models.nodes.receipt_runtime_identity_check.model_receipt_runtime_identity_check_input import (
    ModelReceiptRuntimeIdentityCheckInput,
)
from omnibase_core.models.nodes.receipt_runtime_identity_check.model_receipt_runtime_identity_check_output import (
    ModelReceiptRuntimeIdentityCheckOutput,
)
from omnibase_core.validation.validator_receipt_runtime_identity import (
    DEFAULT_REQUIRED_PACKAGES,
    count_receipts,
    scan_receipt_files,
)


class NodeReceiptRuntimeIdentityCheckCompute:
    """Scan the named receipt files and return violations plus the receipt count."""

    def handle(
        self, request: ModelReceiptRuntimeIdentityCheckInput
    ) -> ModelReceiptRuntimeIdentityCheckOutput:
        """Delegate to the validation-layer scan; no argument parsing or exit codes."""
        paths = [Path(p) for p in request.receipt_paths]
        required = request.required_packages or DEFAULT_REQUIRED_PACKAGES
        violations = scan_receipt_files(paths, required_packages=required)
        return ModelReceiptRuntimeIdentityCheckOutput(
            violations=tuple(violations), receipts_found=count_receipts(paths)
        )
