# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Acceptance criterion model with stable ID for proof linkage."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class ModelAcceptanceCriterion(BaseModel):
    """An individual acceptance criterion with a stable ID for proof linkage.

    The ``id`` field is used as the foreign key in
    ``ModelProofRequirement.criterion_id``. IDs must be stable once assigned —
    do not rename after proof requirements reference them.

    Immutability:
        This model uses ``frozen=True``, making instances immutable after
        creation. This enables safe sharing across threads without
        synchronisation.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    id: str
    statement: str

    @field_validator("id", "statement")
    @classmethod
    def must_be_nonempty(cls, v: str) -> str:
        """Reject empty strings and whitespace-only values."""
        if not v.strip():
            raise ValueError("must be non-empty and not whitespace-only")
        return v


__all__ = ["ModelAcceptanceCriterion"]
