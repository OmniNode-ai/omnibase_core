# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict, Field


class ModelManifestHandler(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(..., min_length=1)
    module_path: str = Field(..., min_length=1)
    routing_strategy: str = Field(..., min_length=1)


__all__ = ["ModelManifestHandler"]
