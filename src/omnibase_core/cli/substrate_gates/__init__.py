# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Substrate gate framework — AST-based enforcement checks for omnibase_core."""

from omnibase_core.cli.substrate_gates._base import (
    BaseGateCheck,
    has_allow_annotation,
    main_for_gate,
)
from omnibase_core.cli.substrate_gates.gate_violation import GateViolation

__all__ = [
    "BaseGateCheck",
    "GateViolation",
    "has_allow_annotation",
    "main_for_gate",
]
