# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Approval token validation result model for the HITL approval flow.

Returned by ``ServiceApprovalTokenValidator.validate()``.

.. versionadded:: 0.20.0  (OMN-2562)
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["ModelApprovalTokenValidationResult"]


@dataclass(frozen=True)
class ModelApprovalTokenValidationResult:
    """Result of validating a HITL approval token.

    Attributes:
        valid: True if the token passed all validation checks.
        command_ref: The command reference (namespaced ID) this token was scoped to.
        principal: The principal identifier extracted from the token
            (or ``None`` if validation failed before extraction).
        rejection_reason: Human-readable explanation of why validation failed.
            ``None`` when ``valid=True``.
        token_jti: The JWT ``jti`` claim (unique token ID) for replay detection.
            ``None`` if the token could not be parsed.
    """

    valid: bool
    command_ref: str
    principal: str | None = field(default=None)
    rejection_reason: str | None = field(default=None)
    token_jti: str | None = field(default=None)
