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

    ``falsifier`` is the check that would show the criterion false;
    ``integrated`` marks a criterion done only when observed in the running
    system.

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
    # Schema 1.1.0 (OMN-23758). Optional here so 1.0.0 files keep loading; a
    # 1.1.0 ticket contract requires both (see ModelTicketContract).
    falsifier: str | None = None
    integrated: bool = False

    @field_validator("id", "statement", "falsifier")
    @classmethod
    def must_be_nonempty(cls, v: str | None) -> str | None:
        """Reject empty strings and whitespace-only values."""
        if v is not None and not v.strip():
            raise ValueError("must be non-empty and not whitespace-only")
        return v


__all__ = ["ModelAcceptanceCriterion"]
