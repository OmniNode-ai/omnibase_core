# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Risk gate result types for the registry-driven CLI.

``GateResult`` is the discriminated union returned by ``ServiceRiskGate.evaluate()``.
Each variant is defined in its own module; this module re-exports all variants
and provides the union alias for use by callers.

.. versionadded:: 0.20.0  (OMN-2562)
"""

from __future__ import annotations

from omnibase_core.models.cli.model_gate_result_dual_approval_required import (
    ModelGateResultDualApprovalRequired,
)
from omnibase_core.models.cli.model_gate_result_hitl_required import (
    ModelGateResultHITLRequired,
)
from omnibase_core.models.cli.model_gate_result_proceed import ModelGateResultProceed
from omnibase_core.models.cli.model_gate_result_prompt_confirmation import (
    ModelGateResultPromptConfirmation,
)

__all__ = [
    "GateResult",
    "ModelGateResultDualApprovalRequired",
    "ModelGateResultHITLRequired",
    "ModelGateResultProceed",
    "ModelGateResultPromptConfirmation",
]

#: Discriminated union of all possible gate results.
GateResult = (
    ModelGateResultProceed
    | ModelGateResultPromptConfirmation
    | ModelGateResultHITLRequired
    | ModelGateResultDualApprovalRequired
)
