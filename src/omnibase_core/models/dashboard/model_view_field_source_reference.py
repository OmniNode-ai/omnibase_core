# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Field source: a reference (OMN-21997)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.dashboard.model_view_slug import ViewSlug

__all__ = ["ModelViewFieldSourceReference"]


class ModelViewFieldSourceReference(BaseModel):
    """Take the value from a named declaration elsewhere in the contract."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source_kind: Literal["reference"] = Field(
        default="reference", description="Discriminator for the field source union"
    )
    ref_id: ViewSlug = Field(
        ..., description="Slug of the declaration this field takes its value from"
    )
