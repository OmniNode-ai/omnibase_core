"""
Model for registry factory representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 RegistryFactory functionality for
factory state management and configuration.

"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_contract_content import ModelContractContent
from omnibase_core.models.core.model_registry_cache_entry import ModelRegistryCacheEntry
from omnibase_core.models.core.model_registry_configuration import (
    ModelRegistryConfiguration,
)


class ModelRegistryFactory(BaseModel):
    """Model representing registry factory state and configuration."""

    registry_cache_metadata: dict[str, ModelRegistryCacheEntry] = Field(
        default_factory=dict,
        description="Registry cache metadata by node ID",
    )
    registry_configurations: dict[str, ModelRegistryConfiguration] = Field(
        default_factory=dict,
        description="Registry configurations by node ID",
    )
    loaded_contracts: dict[str, ModelContractContent] = Field(
        default_factory=dict,
        description="Loaded contract contents for registry creation",
    )
    factory_errors: list[str] = Field(
        default_factory=list,
        description="Factory operation error history",
    )
