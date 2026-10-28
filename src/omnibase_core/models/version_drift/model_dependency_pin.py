# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Consumer paths for an opted-in dependency pin bump (OMN-21478)."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDependencyPin"]


class ModelDependencyPin(BaseModel):
    """The consumer's dependency declaration and lockfile paths."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    pyproject: str = Field(default="pyproject.toml", min_length=1)
    lock: str = Field(default="uv.lock", min_length=1)
