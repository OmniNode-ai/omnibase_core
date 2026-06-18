# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Risk level for UI action-gate policy decisions (OMN-13131, ADR D2).

Scoped to the Contract-Driven UI Platform action-gate policy. Distinct from the
domain-scoped ``routing.EnumRiskLevel`` and ``overseer.EnumRiskLevel``: those
classify routing/dispatch decisions, while this classifies the user-facing risk
of executing a declared UI action (a button = an ``onex.cmd.*`` emitter). Kept
separate so UI affordances and confirmation requirements do not couple to
routing-policy semantics.
"""

from enum import StrEnum


class EnumRiskLevel(StrEnum):
    """Risk level of executing a UI action, lowest to highest."""

    LOW = "low"
    """Low risk — safe to surface without elevated affordances."""

    MEDIUM = "medium"
    """Medium risk — state-modifying; standard confirmation affordance."""

    HIGH = "high"
    """High risk — destructive or hard-to-undo; explicit confirmation."""

    CRITICAL = "critical"
    """Critical risk — irreversible/high-impact; mandatory confirmation."""


__all__: list[str] = ["EnumRiskLevel"]
