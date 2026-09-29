# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""An observation of one item on a declared-state surface."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_declared_state_surface_kind import (
    EnumDeclaredStateSurfaceKind,
)


class ModelDeclaredStateObservation(BaseModel):
    """Read evidence for comparing declared and observed deployment state."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    surface_kind: EnumDeclaredStateSurfaceKind = Field(
        ..., description="Kind of surface that was read."
    )
    surface_id: str = Field(  # string-id-ok: deployment-chosen surface name, not a UUID
        ...,
        min_length=1,
        pattern=r"\S",
        description="Surface on which the item was observed.",
    )
    item_key: str = Field(
        ..., min_length=1, pattern=r"\S", description="Item within the surface."
    )
    observed_digest: str | None = Field(
        ..., description="Observed content digest, or null when unavailable."
    )
    read_ok: bool = Field(..., description="Whether reading the surface succeeded.")
    detail: str = Field(
        ..., description="Read details; required to explain a failed read."
    )

    @model_validator(mode="after")
    def _failed_read_evidence(self) -> Self:
        """Require an explanation and no digest when the read failed."""
        if not self.read_ok:
            if self.observed_digest is not None:
                raise ValueError(
                    "read_ok=False requires observed_digest to be None"
                )  # error-ok: Pydantic validation
            if not self.detail.strip():
                raise ValueError(
                    "read_ok=False requires non-empty detail"
                )  # error-ok: Pydantic validation
        return self


__all__ = ["ModelDeclaredStateObservation"]
