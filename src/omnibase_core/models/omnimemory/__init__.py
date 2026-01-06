# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
OmniMemory Models Module.

This module provides models for OmniMemory cost tracking and billing,
including individual cost entries and cost ledgers.

Key Concepts:
    - **CostEntry**: Individual billable operation with token counts and cost

Example:
    >>> from datetime import datetime, UTC
    >>> from omnibase_core.models.omnimemory import ModelCostEntry
    >>>
    >>> entry = ModelCostEntry(
    ...     timestamp=datetime.now(UTC),
    ...     operation="chat_completion",
    ...     model_used="gpt-4",
    ...     tokens_in=100,
    ...     tokens_out=50,
    ...     cost=0.0045,
    ...     cumulative_total=1.25,
    ... )
    >>> entry.entry_id  # Auto-generated UUID
    UUID('...')

.. versionadded:: 0.6.0
    Added as part of OmniMemory cost tracking (OMN-1239)
"""

from omnibase_core.models.omnimemory.model_cost_entry import ModelCostEntry

__all__ = [
    "ModelCostEntry",
]
