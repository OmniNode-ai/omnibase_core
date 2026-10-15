# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One distribution as a pyproject declares it, across every table (OMN-19998)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDeclaredFloor"]


class ModelDeclaredFloor(BaseModel):
    """A distribution's highest declared lower bound and the requirements seen.

    Attributes:
        floor: The highest lower bound among the requirements, as a release
            tuple, or None when none sets one.
        specifiers: Each requirement string as written.
        bounds: The version-specifier part of each requirement, in the order
            of ``specifiers``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    floor: tuple[int, ...] | None = None
    specifiers: tuple[str, ...] = Field(default=())
    bounds: tuple[str, ...] = Field(default=())
