# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Rule-7a definition-B fold: no I/O and no clock."""

from omnimarket.nodes.node_projection_delegation_disposition.models import (
    ModelDelegationDispositionProjectionRequest,
    ModelDelegationDispositionProjectionResult,
    ModelDelegationDispositionRow,
)


class HandlerProjectionDelegationDisposition:
    """Derive one row with the event's producer-assigned recorded_at."""

    def handle(
        self, request: ModelDelegationDispositionProjectionRequest
    ) -> ModelDelegationDispositionProjectionResult:
        row = ModelDelegationDispositionRow(**request.model_dump())
        return ModelDelegationDispositionProjectionResult(rows=(row,))
