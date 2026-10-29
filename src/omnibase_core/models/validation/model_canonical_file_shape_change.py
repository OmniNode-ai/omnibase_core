# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelCanonicalFileShapeChange -- one path changed from base to head (OMN-21515)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelCanonicalFileShapeChange(BaseModel):
    """A changed path with its status, rename source and both texts.

    ``status`` is the first letter of git's name-status code (A, M, R, C, T);
    a deletion is not a change the shape rules read. ``new_text`` is None for a
    path whose head blob is absent, ``old_text`` None for a path new at base.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    status: str
    path: str
    old_path: str | None = None
    new_text: str | None = None
    old_text: str | None = None
