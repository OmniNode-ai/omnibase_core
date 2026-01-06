# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
OmniMemory Models Module.

This module provides models for OmniMemory cost tracking and billing,
including individual cost entries and cost ledgers for budget management.

Key Concepts:
    - **CostEntry**: Individual billable operation with token counts and cost
    - **CostLedger**: Budget state machine with cost tracking and escalation

Example:
    >>> from datetime import datetime, UTC
    >>> from omnibase_core.models.omnimemory import ModelCostEntry, ModelCostLedger
    >>>
    >>> # Create a budget ledger
    >>> ledger = ModelCostLedger(budget_total=10.0)
    >>>
    >>> # Create a cost entry
    >>> entry = ModelCostEntry(
    ...     timestamp=datetime.now(UTC),
    ...     operation="chat_completion",
    ...     model_used="gpt-4",
    ...     tokens_in=100,
    ...     tokens_out=50,
    ...     cost=0.0045,
    ...     cumulative_total=0.0045,
    ... )
    >>>
    >>> # Add entry to ledger (returns new immutable instance)
    >>> updated_ledger = ledger.with_entry(entry)
    >>> updated_ledger.total_spent
    0.0045

.. versionadded:: 0.6.0
    Added as part of OmniMemory cost tracking (OMN-1239, OMN-1240)
"""

from omnibase_core.models.omnimemory.model_cost_entry import ModelCostEntry
from omnibase_core.models.omnimemory.model_cost_ledger import ModelCostLedger

__all__ = [
    "ModelCostEntry",
    "ModelCostLedger",
]
