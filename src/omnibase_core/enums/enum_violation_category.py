# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Violation category enumeration for architectural invariant contracts."""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumViolationCategory(StrValueHelper, str, Enum):
    """Category of an architectural invariant violation."""

    STATIC_ARCHITECTURE = "static_architecture"
    """Repo layering, import direction, or dependency graph violation."""

    RUNTIME_TOPOLOGY = "runtime_topology"
    """Node kind constraints, handler output purity, or execution shape violation."""

    CONTRACT_VIOLATION = "contract_violation"
    """Hardcoded topic strings, missing contract.yaml declarations, or schema drift."""

    PROJECTION_AUTHORITY = "projection_authority"
    """Client rendering truth rather than consuming authoritative projections."""

    RECEIPT_GOVERNANCE = "receipt_governance"
    """Missing dod_evidence, self-signed receipt, or missing verifier provenance."""


__all__ = ["EnumViolationCategory"]
