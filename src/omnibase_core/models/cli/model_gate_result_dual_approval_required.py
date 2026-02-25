# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
GateResultDualApprovalRequired — CRITICAL-risk gate, requires two principal tokens.

.. versionadded:: 0.20.0  (OMN-2562)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from omnibase_core.enums.enum_cli_command_risk import EnumCliCommandRisk
from omnibase_core.enums.enum_risk_gate_outcome import EnumRiskGateOutcome

__all__ = ["GateResultDualApprovalRequired"]


@dataclass(frozen=True)
class GateResultDualApprovalRequired:
    """CRITICAL-risk gate — requires two distinct principal approval tokens.

    The CLI must collect two separate tokens from two different principals,
    then validate each independently via ``ApprovalTokenValidator.validate()``.

    Attributes:
        command_ref: The namespaced command reference being dispatched.
        risk: The risk level of the command.
        challenge_message: Message explaining the dual-approval requirement.
        outcome: Always ``EnumRiskGateOutcome.DUAL_APPROVAL_REQUIRED``.
        evaluated_at: UTC timestamp of the gate evaluation.
    """

    command_ref: str
    risk: EnumCliCommandRisk
    challenge_message: str
    outcome: EnumRiskGateOutcome = field(
        default=EnumRiskGateOutcome.DUAL_APPROVAL_REQUIRED
    )
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
