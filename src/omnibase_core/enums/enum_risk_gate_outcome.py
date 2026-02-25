# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Risk gate outcome enum for the registry-driven CLI.

Records the decision made by RiskGate.evaluate() for audit logging.

.. versionadded:: 0.20.0  (OMN-2562)
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumRiskGateOutcome"]


@unique
class EnumRiskGateOutcome(StrValueHelper, str, Enum):
    """Outcome of a risk gate evaluation.

    Values:
        PROCEED: Gate passed — dispatch proceeds without interruption.
        CONFIRMATION_REQUIRED: User must confirm (y/N prompt) before dispatch.
        CONFIRMED: User provided explicit confirmation; dispatch proceeds.
        REJECTED: User declined confirmation or did not provide approval token.
        HITL_TOKEN_REQUIRED: HIGH-risk command requires an approval token.
        HITL_TOKEN_VALID: Provided approval token passed validation.
        HITL_TOKEN_INVALID: Provided approval token failed validation.
        DUAL_APPROVAL_REQUIRED: CRITICAL-risk command requires two distinct tokens.
        DUAL_APPROVAL_VALID: Both approval tokens passed validation.
        DUAL_APPROVAL_INVALID: One or both dual-approval tokens failed validation.
    """

    PROCEED = "proceed"
    CONFIRMATION_REQUIRED = "confirmation_required"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    HITL_TOKEN_REQUIRED = "hitl_token_required"
    HITL_TOKEN_VALID = "hitl_token_valid"
    HITL_TOKEN_INVALID = "hitl_token_invalid"
    DUAL_APPROVAL_REQUIRED = "dual_approval_required"
    DUAL_APPROVAL_VALID = "dual_approval_valid"
    DUAL_APPROVAL_INVALID = "dual_approval_invalid"
