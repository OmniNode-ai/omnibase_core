# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed view of the node_done_write_receipt_gate_compute handler module surface.

A caller that binds the node from its packaged contract checks every member of
this protocol against the handler module's ``__all__`` before use.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from omnibase_core.models.ticket.model_ac_binding_row import ModelAcBindingRow
from omnibase_core.models.ticket.model_done_write_decision import ModelDoneWriteDecision
from omnibase_core.models.ticket.model_done_write_receipt_request import (
    ModelDoneWriteReceiptRequest,
)
from omnibase_core.nodes.node_done_write_receipt_gate_compute.protocol_done_write_receipt_queries import (
    ProtocolDoneWriteReceiptQueries,
)


@runtime_checkable
class ProtocolDoneWriteReceiptGate(ProtocolDoneWriteReceiptQueries, Protocol):
    """Decide Done writes and expose the contract handler's public helpers."""

    def decide(self, request: ModelDoneWriteReceiptRequest) -> ModelDoneWriteDecision:
        """Apply the node's declared handler."""
        ...

    def ac_binding_gap(
        self, description: str, verdict: dict[str, object], ticket_id: str
    ) -> tuple[str, tuple[str, ...], tuple[ModelAcBindingRow, ...]]:
        """Delegate to the exported ac_binding_gap function."""
        ...

    def verdict_is_all_verified(self, verdict: Mapping[str, object]) -> bool:
        """Delegate to the exported verdict_is_all_verified function."""
        ...

    def evaluate_done_write_receipt(
        self, *, ticket_id: str, description: str, verdict: Mapping[str, object] | None
    ) -> ModelDoneWriteDecision:
        """Delegate to the exported evaluate_done_write_receipt function."""
        ...


__all__ = ["ProtocolDoneWriteReceiptGate"]
