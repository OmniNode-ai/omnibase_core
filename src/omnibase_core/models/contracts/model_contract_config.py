# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Strongly typed top-level contract config model (OMN-11430).

Composes LLM endpoint, storage, and operational sub-models.
extra="allow" so node-specific fields not covered by the base schema pass through.
Sub-models use extra="forbid" for strict validation within their scope.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.model_llm_endpoint_config import (
    ModelLlmEndpointConfig,
)
from omnibase_core.models.contracts.model_operational_config import (
    ModelOperationalConfig,
)
from omnibase_core.models.contracts.model_storage_config import ModelStorageConfig


class ModelContractConfig(BaseModel):
    """
    Strongly typed contract config block.

    Composes LLM endpoint, storage, and operational sub-models as optional
    nested structures. extra="allow" lets node-specific fields not covered by
    the base schema pass through at the top level — node-specific typed config
    models are a follow-up.

    All fields default to empty sub-models so contracts without a config section
    still load cleanly.
    """

    model_config = ConfigDict(frozen=True, extra="allow", from_attributes=True)

    llm: ModelLlmEndpointConfig = Field(
        default_factory=ModelLlmEndpointConfig,
        description="LLM endpoint configuration",
    )
    storage: ModelStorageConfig = Field(
        default_factory=ModelStorageConfig,
        description="Storage connection configuration",
    )
    operational: ModelOperationalConfig = Field(
        default_factory=ModelOperationalConfig,
        description="Operational configuration",
    )
