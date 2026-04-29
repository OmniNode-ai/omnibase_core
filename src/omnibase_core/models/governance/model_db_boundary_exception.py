# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""DB Boundary Exception Model."""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.governance.enum_db_boundary import (
    EnumDbBoundaryExceptionStatus,
    EnumDbBoundaryReasonCategory,
)

# YYYY-MM pattern for review_by field
_REVIEW_BY_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class ModelDbBoundaryException(BaseModel):
    """A registered DB boundary exception.

    Documents an approved deviation from the one-service-one-database principle.
    Each exception must have a review date and explicit justification.
    """

    model_config = ConfigDict(frozen=True)

    repo: str = Field(..., description="Repository containing the exception")
    file: str = Field(..., description="Exact file path within the repository")
    usage: str = Field(
        ..., description="Brief description of the cross-boundary access"
    )
    reason_category: EnumDbBoundaryReasonCategory = Field(
        ..., description="Category of the exception reason"
    )
    justification: str = Field(..., description="Explicit rationale for the exception")
    owner: str = Field(..., description="Person or team responsible for the exception")
    approved_by: str = Field(..., description="Person who approved the exception")
    review_by: str = Field(
        ..., description="YYYY-MM date when the exception must be re-evaluated"
    )
    status: EnumDbBoundaryExceptionStatus = Field(
        default=EnumDbBoundaryExceptionStatus.APPROVED,
        description="Current status of the exception",
    )

    @field_validator("review_by")
    @classmethod
    def validate_review_by(cls, v: str) -> str:
        """Validate review_by is YYYY-MM format with valid month (01-12)."""
        if not _REVIEW_BY_PATTERN.match(v):
            msg = (
                f"Invalid review_by format: {v}. "
                "Expected YYYY-MM with valid month (01-12)"
            )
            raise ValueError(msg)
        return v
