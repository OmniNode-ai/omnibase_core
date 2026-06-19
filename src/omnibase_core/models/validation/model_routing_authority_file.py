# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Loaded-file payload model for the routing-authority validator (OMN-13285)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelRoutingAuthorityFile(BaseModel):
    """A single loaded file (repo-relative path + raw text).

    The runner / EFFECT boundary loads the file from disk; the COMPUTE validator
    receives only this typed value so it never performs I/O itself.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Repo-relative path of the loaded file.")
    text: str = Field(
        description="Full UTF-8 text of the file (loaded at the boundary)."
    )


__all__ = ["ModelRoutingAuthorityFile"]
