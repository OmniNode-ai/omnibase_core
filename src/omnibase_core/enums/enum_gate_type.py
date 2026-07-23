# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Gate type enum for objective function hard gates.

Defines the types of hard gates that can be evaluated in an ObjectiveSpec.
Part of the objective functions and reward architecture (OMN-2537).
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper

__all__ = ["EnumGateType"]


@unique
class EnumGateType(UtilStrValueHelper, str, Enum):
    """Types of hard gates in an objective evaluation.

    Hard gates are binary pass/fail checks evaluated before shaped reward terms.
    If any gate fails, the run fails regardless of shaped metrics.

    Attributes:
        TEST_PASS: All tests must pass (pytest / test runner output).
        GATE_PASS: A named validator gate must pass (contract-defined).
        BUDGET: Cost must not exceed declared budget ceiling.
        LATENCY: Execution latency must not exceed declared threshold.
        SCHEMA_FINGERPRINT: Schema fingerprint must match expected value.
        SECURITY: No security violations detected (PII, blacklist, etc.).
        BLACKLIST: No blacklisted commands or patterns invoked.
    """

    TEST_PASS = "test_pass"
    """All tests must pass (pytest / test runner structured output)."""

    GATE_PASS = "gate_pass"
    """A named validator gate must pass (contract-defined check)."""

    BUDGET = "budget"
    """Cost must not exceed the declared budget ceiling."""

    LATENCY = "latency"
    """Execution latency must not exceed the declared threshold."""

    SCHEMA_FINGERPRINT = "schema_fingerprint"
    """Schema fingerprint must match the expected tamper-evident hash."""

    SECURITY = "security"
    """No security violations (PII exposure, credential leaks, etc.)."""

    BLACKLIST = "blacklist"
    """No blacklisted commands or patterns were invoked."""
