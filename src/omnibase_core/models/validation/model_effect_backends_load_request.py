# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelEffectBackendsLoadRequest (OMN-22911)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelEffectBackendsLoadRequest(BaseModel):
    """The directory of node folders (each holding a contract.yaml) to read."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    root: str = Field(description="Directory whose children are node folders")
