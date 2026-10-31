# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result of one deterministic experiment evaluation (OMN-21627)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumRetrospectiveVerdict(UtilStrValueHelper, str, Enum):
    """The three results of the evaluator, in fixed precedence.

    Attributes:
        FAIL: Valid evidence proves a predeclared safety failure, or mature evidence misses a target or guardrail.
        INSUFFICIENT_EVIDENCE: No proven safety failure, but the contract or the evidence is incomplete, immature, conflicting or below its floor.
        PASS: Valid mature evidence satisfies every required target and guardrail.
    """

    FAIL = "fail"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    PASS = "pass"
