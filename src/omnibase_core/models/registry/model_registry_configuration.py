"""
ModelRegistryConfiguration - Registry configuration status model.
"""

from pydantic import BaseModel


class ModelRegistryConfiguration(BaseModel):
    """Registry configuration information."""

    cache_enabled: bool
    validation_required: bool
    health_check_timeout_ms: int
