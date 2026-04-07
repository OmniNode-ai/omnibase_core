# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
DoD Evidence Model for ONEX contracts.

Defines structured evidence items for Definition of Done verification.
Each evidence item specifies a type and a check command or reference
that can be validated programmatically.

.. versionadded:: 0.35.0
    Added as part of golden_path contract schema (OMN-7731)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelDodEvidence(BaseModel):
    """Structured evidence item for Definition of Done verification.

    Each evidence item declares what type of verification is required
    and how to perform or locate the verification.

    Attributes:
        type: Evidence category (e.g., "rendered_output", "integration_test",
            "golden_chain", "api_response", "screenshot").
        description: Human-readable description of what this evidence proves.
        check: Optional command, URL, or test path that validates this evidence.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    type: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Evidence category (e.g., 'rendered_output', 'integration_test', 'golden_chain')",
    )

    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Human-readable description of what this evidence proves",
    )

    check: str | None = Field(
        default=None,
        max_length=500,
        description="Command, URL, or test path that validates this evidence",
    )


__all__ = [
    "ModelDodEvidence",
]
