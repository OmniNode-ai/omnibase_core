# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The facts document a venv gate hands to the build-lock validator (OMN-22649)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.venv_build_lock.model_venv_build_lock_surface import (
    ModelVenvBuildLockSurface,
)


class ModelVenvBuildLockDocument(BaseModel):
    """The checkout's lock and every venv surface the gate read."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    checkout_lock_path: str = Field(
        description="Path of the lock of the checkout being committed"
    )
    surfaces: tuple[ModelVenvBuildLockSurface, ...] = Field(
        description="Every venv surface the gate read back"
    )
