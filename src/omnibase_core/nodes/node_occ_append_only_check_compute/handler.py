# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""NodeOccAppendOnlyCheckCompute — OCC append-only COMPUTE handler.

Pure and deterministic: the parsed contracts and git change lists arrive on the
request; all git and filesystem I/O happens in the runtime, never here. The
evaluation lives in ``omnibase_core.validation.validator_occ_append_only``.

Ticket: OMN-21520 (gate: OMN-13888, OMN-19050).
"""

from __future__ import annotations

from omnibase_core.models.nodes.occ_append_only_check.model_occ_append_only_check_input import (
    ModelOccAppendOnlyCheckInput,
)
from omnibase_core.models.validation.model_occ_append_only_result import (
    ModelOccAppendOnlyResult,
)
from omnibase_core.validation.validator_occ_append_only import evaluate_append_only

__all__ = ["NodeOccAppendOnlyCheckCompute"]


class NodeOccAppendOnlyCheckCompute:
    """COMPUTE handler that evaluates the OCC append-only invariant."""

    def handle(self, request: ModelOccAppendOnlyCheckInput) -> ModelOccAppendOnlyResult:
        """Return the append-only verdict for the supplied contracts and diffs."""
        return evaluate_append_only(
            request.base_contract,
            request.head_contract,
            request.receipt_diff,
            request.branch_history,
        )
