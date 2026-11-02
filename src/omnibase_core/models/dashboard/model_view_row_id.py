# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Row identity for view documents (OMN-21997; view-centric plan §10.1).

A row id is the view id, the section id and the values of the exposure's
declared unique key. It is never an ``order_by`` position: a position changes
when an upstream row is inserted, which would make every row below it look new.
Whether a view's rows actually carry their exposure's key is enforced by the
preflight, a later ticket; this model only makes the identity a typed field.
"""

from __future__ import annotations

from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.dashboard.model_view_slug import ViewSlug

__all__ = ["ModelViewRowId"]


class ModelViewRowId(BaseModel):
    """Identity of one row: view, section and declared unique-key values."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    view_id: ViewSlug = Field(..., description="Slug of the view the row belongs to")
    section_id: ViewSlug = Field(
        ..., description="Slug of the section the row belongs to"
    )
    key_values: tuple[str, ...] = Field(
        ...,
        min_length=1,
        description=(
            "Values of the exposure's declared unique key, in declared order. "
            "Never an order_by position."
        ),
    )

    @field_validator("key_values")
    @classmethod
    def validate_key_values_non_empty(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Refuse an empty key value; an empty part identifies nothing.

        Raises:
            ValueError: If any key value is the empty string.
        """
        if any(part == "" for part in value):
            raise ValueError("key_values must not contain an empty value")
        return value

    def as_string(self) -> str:
        """Return the id as one string, ``view/section/key...``.

        Each part is percent-encoded, so a ``/`` inside a key value cannot be
        read as a separator and two distinct ids never render alike.
        """
        parts = (self.view_id, self.section_id, *self.key_values)
        return "/".join(quote(part, safe="") for part in parts)
