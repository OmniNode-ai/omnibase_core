# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_sibling_stale_parameters import (
    ModelSiblingStaleParameters,
)


class ModelFirstPartyTagInventoryRequest(BaseModel):
    """Effect dependencies are explicit request data supplied by the container."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    repo: str = Field(min_length=1)
    policy: ModelSiblingStaleParameters
