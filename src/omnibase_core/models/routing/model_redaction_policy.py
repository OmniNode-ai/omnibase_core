# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Redaction policy model for field-level data redaction rules.

Defines named redaction policies that map field patterns to redaction
strategies. Used by classification gates to enforce data protection
during tiered resolution.

.. versionadded:: 0.21.0
    Phase 4 of authenticated dependency resolution (OMN-2893).
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelRedactionPolicy"]


class ModelRedactionPolicy(BaseModel):
    """Named redaction policy with field-level redaction rules.

    Each policy defines a set of rules that map field name patterns
    to redaction strategies. During resolution, fields matching the
    patterns are redacted according to the specified strategy before
    data crosses trust boundaries.

    Attributes:
        policy_name: Unique name identifying this redaction policy
            (e.g., ``"pii_masked"``, ``"full_redact"``).
        rules: Mapping of field name patterns to redaction strategies.
            Keys are glob-style patterns (e.g., ``"*.email"``,
            ``"user.ssn"``). Values are strategy names (e.g.,
            ``"mask"``, ``"hash"``, ``"remove"``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    policy_name: str = Field(
        description="Unique name for this redaction policy",
        min_length=1,
    )

    rules: dict[str, str] = Field(
        default_factory=dict,
        description="Field pattern to redaction strategy mapping",
    )
