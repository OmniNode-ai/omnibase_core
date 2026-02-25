# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
GateResultHITLRequired — HIGH-risk gate, requires a one-time HITL approval token.

.. versionadded:: 0.20.0  (OMN-2562)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from omnibase_core.enums.enum_cli_command_risk import EnumCliCommandRisk
from omnibase_core.enums.enum_risk_gate_outcome import EnumRiskGateOutcome

__all__ = ["ModelGateResultHITLRequired"]


@dataclass(frozen=True)
class ModelGateResultHITLRequired:
    """HIGH-risk gate — requires a one-time HITL approval token.

    The CLI must:
    1. Display command details and risk classification.
    2. Display the approval challenge (URL or token prompt).
    3. Collect the token via ``--approval-token`` or interactive prompt.
    4. Pass the token to ``ApprovalTokenValidator.validate()``.

    Attributes:
        command_ref: The namespaced command reference being dispatched.
        risk: The risk level of the command.
        challenge_message: Message explaining how to obtain the approval token.
        outcome: Always ``EnumRiskGateOutcome.HITL_TOKEN_REQUIRED``.
        evaluated_at: UTC timestamp of the gate evaluation.
    """

    command_ref: str
    risk: EnumCliCommandRisk
    challenge_message: str
    outcome: EnumRiskGateOutcome = field(
        default=EnumRiskGateOutcome.HITL_TOKEN_REQUIRED
    )
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
