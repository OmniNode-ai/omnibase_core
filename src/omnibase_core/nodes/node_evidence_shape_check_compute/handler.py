# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pure typed evidence-shape validation, with no bus or runtime dependencies."""

from __future__ import annotations

from omnibase_core.models.contracts.ticket.model_receipt_gate_result import (
    ModelReceiptGateResult,
)
from omnibase_core.models.nodes.evidence_shape_check.model_evidence_shape_check_input import (
    ModelEvidenceShapeCheckInput,
)
from omnibase_core.validation.validator_receipt_gate import check_evidence_source_shape


class NodeEvidenceShapeCheckCompute:
    """Check the Evidence-Source block shape of a supplied PR body."""

    def handle(self, request: ModelEvidenceShapeCheckInput) -> ModelReceiptGateResult:
        """Delegate to the pure shape checker."""
        return check_evidence_source_shape(request.pr_body)
