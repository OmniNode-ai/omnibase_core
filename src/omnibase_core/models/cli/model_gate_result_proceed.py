# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
GateResultProceed — risk gate passed, dispatch proceeds immediately.

.. versionadded:: 0.20.0  (OMN-2562)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from omnibase_core.enums.enum_cli_command_risk import EnumCliCommandRisk
from omnibase_core.enums.enum_risk_gate_outcome import EnumRiskGateOutcome

__all__ = ["GateResultProceed"]


@dataclass(frozen=True)
class GateResultProceed:
    """Risk gate passed — dispatch proceeds immediately.

    Used for LOW-risk commands (no gate required) and after successful
    confirmation / token validation.

    Attributes:
        command_ref: The namespaced command reference being dispatched.
        risk: The risk level of the command.
        outcome: Always ``EnumRiskGateOutcome.PROCEED``.
        evaluated_at: UTC timestamp of the gate evaluation.
    """

    command_ref: str
    risk: EnumCliCommandRisk
    outcome: EnumRiskGateOutcome = field(default=EnumRiskGateOutcome.PROCEED)
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
