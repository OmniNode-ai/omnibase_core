# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Thin COMPUTE handler over the receipt re-probe validator (OMN-9789)."""

from __future__ import annotations

from pathlib import Path

from omnibase_core.models.contracts.ticket.model_receipt_reprobe_report import (
    ModelReceiptReprobeReport,
)
from omnibase_core.models.nodes.receipt_reprobe_check.model_receipt_reprobe_check_input import (
    ModelReceiptReprobeCheckInput,
)
from omnibase_core.validation.validator_receipt_reprobe import (
    verify_receipts_by_reexecuting_probes,
)


class NodeReceiptReprobeCheckCompute:
    """Re-probe every receipt under the requested directory."""

    def handle(
        self, request: ModelReceiptReprobeCheckInput
    ) -> ModelReceiptReprobeReport:
        return verify_receipts_by_reexecuting_probes(Path(request.receipts_dir))
