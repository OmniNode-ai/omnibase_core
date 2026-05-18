# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict, Field


class ModelManifestContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    node_type: str = Field(..., min_length=1)
    contract_hash: str = Field(..., min_length=1)


__all__ = ["ModelManifestContract"]
