# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The latest registry change a runtime has seen for one name (OMN-21226)."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_contract_hotload_operation import (
    EnumContractHotloadOperation,
)

__all__ = ["ModelHotloadObservedEntry"]


class ModelHotloadObservedEntry(BaseModel):
    """The latest registry change the runtime has seen for one name."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    registry_version: int = Field(ge=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation: EnumContractHotloadOperation
