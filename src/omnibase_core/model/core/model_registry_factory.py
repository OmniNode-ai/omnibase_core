"""
Model for registry factory representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 RegistryFactory functionality for
factory state management and configuration.

Author: ONEX Framework Team
"""

from typing import Dict, List

from pydantic import BaseModel, Field

from omnibase_core.core.models.model_contract_content import \
    ModelContractContent
from omnibase_core.core.models.model_registry_cache_entry import \
    ModelRegistryCacheEntry
from omnibase_core.core.models.model_registry_configuration import \
    ModelRegistryConfiguration


class ModelRegistryFactory(BaseModel):
    """Model representing registry factory state and configuration."""

    registry_cache_metadata: Dict[str, ModelRegistryCacheEntry] = Field(
        default_factory=dict, description="Registry cache metadata by node ID"
    )
    registry_configurations: Dict[str, ModelRegistryConfiguration] = Field(
        default_factory=dict, description="Registry configurations by node ID"
    )
    loaded_contracts: Dict[str, ModelContractContent] = Field(
        default_factory=dict,
        description="Loaded contract contents for registry creation",
    )
    factory_errors: List[str] = Field(
        default_factory=list, description="Factory operation error history"
    )
