# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The scope an overlay document is read for (OMN-19391).

A store document lives at one ``(environment, lane)`` pair; a reader asks for a
key within a scope (plan task B3's ``get_document(key, scope)``).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# One path segment of a store location: lowercase, no separator, no dot-dot.
_SEGMENT_PATTERN = r"^[a-z0-9][a-z0-9-]*$"


class ModelConfigOverlayScope(BaseModel):
    """An ``(environment, lane)`` pair naming where overlay documents live."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    environment: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=_SEGMENT_PATTERN,
        description="Deployment environment the documents belong to.",
    )
    lane: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=_SEGMENT_PATTERN,
        description="Runtime lane within the environment.",
    )


__all__ = ["ModelConfigOverlayScope"]
