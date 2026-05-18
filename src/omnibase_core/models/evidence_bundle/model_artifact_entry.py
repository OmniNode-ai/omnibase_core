# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelArtifactEntry — single artifact record within a bundle manifest."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelArtifactEntry(BaseModel):
    """Single artifact record within a bundle manifest."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    filename: str
    sha256: str
    write_order: int


__all__ = ["ModelArtifactEntry"]
