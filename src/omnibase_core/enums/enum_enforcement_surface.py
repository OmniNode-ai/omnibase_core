# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Enforcement surface enumeration for architectural invariant contracts."""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumEnforcementSurface(UtilStrValueHelper, str, Enum):
    """Surfaces where an architectural invariant is enforced."""

    STATIC_ARCHITECTURE = "static_architecture"
    """AST/static analysis at commit time (pre-commit hooks, CI validators)."""

    CI_GATE = "ci_gate"
    """Required CI status check that blocks merge on violation."""

    PRE_TOOL_USE = "pre_tool_use"
    """Claude Code PreToolUse hook — developer ergonomics, not authoritative."""

    RUNTIME_VALIDATION = "runtime_validation"
    """Runtime guard enforced by the ONEX runtime before handler execution."""

    CONTRACT_VALIDATION = "contract_validation"
    """Contract YAML schema / cross-repo drift validation."""


__all__ = ["EnumEnforcementSurface"]
