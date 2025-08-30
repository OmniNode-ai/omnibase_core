"""
Registry state model for OmniMemory system.

Represents the current state of the service registry.
"""

from typing import Dict, List

from pydantic import BaseModel, Field

from omnibase_core.model.omnimemory.model_service_instance import \
    ModelServiceInstance


class ModelRegistryState(BaseModel):
    """Represents the current state of the service registry."""

    services: Dict[str, ModelServiceInstance] = Field(
        default_factory=dict, description="Dictionary of registered services"
    )
    initialized: bool = Field(
        default=False, description="Whether the registry is initialized"
    )
    initialization_errors: List[str] = Field(
        default_factory=list, description="List of initialization errors"
    )
