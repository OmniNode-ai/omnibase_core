# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One module-level function, as a fact for the handler-shape check (OMN-21536)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelHandlerShapeFunction"]


class ModelHandlerShapeFunction(BaseModel):
    """A module-level function name and its line."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str
    line: int
