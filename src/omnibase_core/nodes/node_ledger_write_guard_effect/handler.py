# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Node entry point for the ledger guard shared with the CLI."""

from __future__ import annotations

from omnibase_core.handlers.handler_ledger_write_guard import HandlerLedgerWriteGuard
from omnibase_core.models.ledger_write_guard.model_ledger_write_guard_decision import (
    ModelLedgerWriteGuardDecision,
)
from omnibase_core.models.ledger_write_guard.model_ledger_write_guard_request import (
    ModelLedgerWriteGuardRequest,
)


class NodeLedgerWriteGuardEffect:
    """Expose the shared guard through a node-local default handler.

    The implementation stays in handlers so the ledger CLI can use it without
    importing the nodes layer.
    """

    def handle(
        self, request: ModelLedgerWriteGuardRequest
    ) -> ModelLedgerWriteGuardDecision:
        """Classify the requested target using the shared test-write guard."""
        return HandlerLedgerWriteGuard().handle(request)
