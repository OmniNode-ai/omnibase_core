# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.utils.util_decorators import allow_string_id

__all__ = ["ModelPlanTicketLink", "PlanTicketLink"]

_PLAN_ID_PATTERN = re.compile(r"^P[1-9][0-9]*(?:_[1-9][0-9]*)?$")
_TICKET_ID_PATTERN = re.compile(r"^OMN-[0-9]+$")


@allow_string_id(reason="Plan entry ID and Linear ticket ID are external identifiers")
class ModelPlanTicketLink(BaseModel):
    """Frozen sub-model linking a plan entry to a Linear ticket.

    Immutability:
        This model uses frozen=True, making instances immutable after creation.
        This enables safe sharing across threads without synchronization.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # string-id-ok: Plan entry ID is an external P-format identifier (e.g., P1, P3_1)
    entry_id: str = Field(
        ...,
        description=(
            "Plan entry ID in P{N} format (e.g., P1, P12, P3_1). "
            "Must match ^P[1-9][0-9]*(?:_[1-9][0-9]*)?$."
        ),
    )
    # string-id-ok: External Linear ticket identifier (e.g., OMN-1234)
    ticket_id: str = Field(
        ...,
        description=(
            "Linear ticket ID in OMN-{N} format (e.g., OMN-1234). "
            "Must match ^OMN-[0-9]+$."
        ),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="When the link was created (UTC).",
    )

    @field_validator("entry_id", mode="before")
    @classmethod
    def _normalize_and_validate_entry_id(cls, v: str) -> str:
        """Strip whitespace, uppercase p -> P, then validate pattern."""
        if not isinstance(v, str):
            # error-ok: Pydantic field_validator requires ValueError/TypeError
            raise TypeError(f"entry_id must be a string, got {type(v).__name__}")
        normalized = v.strip()
        if normalized.startswith("p"):
            normalized = "P" + normalized[1:]
        if not _PLAN_ID_PATTERN.match(normalized):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"entry_id {normalized!r} does not match pattern "
                f"^P[1-9][0-9]*(?:_[1-9][0-9]*)?$ (e.g., P1, P12, P3_1)"
            )
        return normalized

    @field_validator("ticket_id", mode="before")
    @classmethod
    def _normalize_and_validate_ticket_id(cls, v: str) -> str:
        """Strip whitespace, normalize case, then validate pattern."""
        if not isinstance(v, str):
            # error-ok: Pydantic field_validator requires ValueError/TypeError
            raise TypeError(f"ticket_id must be a string, got {type(v).__name__}")
        normalized = v.strip()
        if normalized.upper().startswith("OMN-"):
            normalized = "OMN-" + normalized[4:]
        if not _TICKET_ID_PATTERN.match(normalized):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"ticket_id {normalized!r} does not match pattern "
                f"^OMN-[0-9]+$ (e.g., OMN-1234)"
            )
        return normalized

    @field_validator("created_at", mode="before")
    @classmethod
    def _enforce_utc_timezone(cls, v: Any) -> Any:
        """Enforce UTC timezone on datetime fields during deserialization.

        Naive datetimes (no timezone info) are assumed UTC and have the UTC
        timezone attached. Datetimes with a non-UTC timezone are converted
        to UTC. Already-UTC datetimes pass through unchanged.
        """
        if not isinstance(v, datetime):
            return v
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v.astimezone(UTC)


PlanTicketLink = ModelPlanTicketLink
