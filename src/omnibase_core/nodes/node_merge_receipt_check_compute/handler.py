# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pure canonical COMPUTE handler for the report-only merge-side receipt check."""

from omnibase_core.models.merge_receipt.model_merge_receipt_check_input import (
    ModelMergeReceiptCheckInput,
)
from omnibase_core.models.merge_receipt.model_merge_receipt_check_result import (
    ModelMergeReceiptCheckResult,
)
from omnibase_core.validation.checker_merge_receipt import check_merge_receipt


class NodeMergeReceiptCheckCompute:
    """Judge supplied pull-request facts against the contract without I/O."""

    def handle(
        self, request: ModelMergeReceiptCheckInput
    ) -> ModelMergeReceiptCheckResult:
        """Return the would-refuse verdicts; the exit code is always zero."""
        return check_merge_receipt(request)
