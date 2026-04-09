# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Node Role Enum.

Declares each node's architectural role in a domain pipeline,
enabling composable decomposition of complex workflows.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumNodeRole(StrValueHelper, str, Enum):
    """
    Architectural role of a node within a domain pipeline.

    Declares what functional responsibility a node fulfills, enabling
    composable decomposition: inventory -> triage -> fix -> report.
    """

    INVENTORY = "inventory"
    """Discovers and catalogs available resources or items."""

    TRIAGE = "triage"
    """Classifies and prioritizes items for further processing."""

    FIX = "fix"
    """Applies corrective actions to identified issues."""

    PROBE = "probe"
    """Inspects or queries external systems for current state."""

    REPORT = "report"
    """Produces human-readable or structured output from processed data."""

    ORCHESTRATOR = "orchestrator"
    """Coordinates multi-step workflows across other nodes."""

    REDUCER = "reducer"
    """Aggregates or accumulates state from a stream of events."""

    EFFECT = "effect"
    """Performs external I/O: API calls, file writes, notifications."""

    INTERNAL = "internal"
    """Infrastructure or utility nodes not part of a domain pipeline."""


__all__ = ["EnumNodeRole"]
