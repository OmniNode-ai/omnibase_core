# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A contract fragment the caller's renderer accepted, with its drawing for each view it offers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelLoadedDiagramFragment(BaseModel):
    """The kind of a fragment and the Mermaid text its renderer drew for each offered view."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: str = Field(
        description="The block the fragment holds, as the marker names it"
    )
    drawings: dict[str, str] = Field(
        default_factory=dict,
        description="Mermaid text by view name; a view the renderer does not offer is absent",
    )
