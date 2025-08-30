"""
ModelRegistryDependencies - Registry dependency status model.
"""

from pydantic import BaseModel


class ModelRegistryDependencies(BaseModel):
    """Registry dependency status information."""

    event_bus_available: bool
    config_provided: bool
