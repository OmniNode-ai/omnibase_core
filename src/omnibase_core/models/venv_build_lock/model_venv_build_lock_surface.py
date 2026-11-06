# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One venv surface and the lock it was built from (OMN-22649)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelVenvBuildLockSurface(BaseModel):
    """What a venv has installed, and the lock that venv was built from.

    The build lock is the lock the surface answers to: the lock of the checkout that
    holds a ``.venv``, or the lock a plugin venv's built-from marker names. It is never
    the lock of a checkout that has not built the surface.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    label: str = Field(description="Names the surface in a finding")
    build_lock_path: str = Field(
        description="Path of the lock the surface was built from"
    )
    build_lock_text: str | None = Field(
        default=None,
        description="Text of that lock; absent until a reader supplies it, and a surface "
        "whose lock cannot be read is refused",
    )
    installed: dict[str, str] = Field(
        default_factory=dict,
        description="Registry distribution name to installed version",
    )
    installed_git: dict[str, str] = Field(
        default_factory=dict,
        description="Git-sourced distribution name to installed commit",
    )
