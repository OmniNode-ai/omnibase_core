# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelGateResultPromptConfirmation — MEDIUM-risk gate, requires user confirmation.

.. versionadded:: 0.20.0  (OMN-2562)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from omnibase_core.enums.enum_cli_command_risk import EnumCliCommandRisk
from omnibase_core.enums.enum_risk_gate_outcome import EnumRiskGateOutcome

__all__ = ["ModelGateResultPromptConfirmation"]


@dataclass(frozen=True)
class ModelGateResultPromptConfirmation:
    """MEDIUM-risk gate — requires user confirmation prompt (y/N).

    The CLI must display the prompt and collect input before proceeding.
    The default must be "No" (safe default).

    Attributes:
        command_ref: The namespaced command reference being dispatched.
        risk: The risk level of the command.
        prompt_message: Human-readable confirmation message to display.
        outcome: Always ``EnumRiskGateOutcome.CONFIRMATION_REQUIRED``.
        evaluated_at: UTC timestamp of the gate evaluation.
    """

    command_ref: str
    risk: EnumCliCommandRisk
    prompt_message: str
    outcome: EnumRiskGateOutcome = field(
        default=EnumRiskGateOutcome.CONFIRMATION_REQUIRED
    )
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
