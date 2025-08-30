"""
ModelRegistryStatus - Registry status model for ALL ONEX registries.
"""

from pydantic import BaseModel

from .model_registry_configuration import ModelRegistryConfiguration
from .model_registry_dependencies import ModelRegistryDependencies
from .model_registry_tool_info import ModelRegistryToolInfo


class ModelRegistryStatus(BaseModel):
    """
    Registry status model for ALL ONEX registries.

    Replaces Dict[str, Union[...]] violations with proper Pydantic model.
    This model should be used by ALL registries, not duplicated per tool.
    """

    registry_type: str
    registry_class: str
    initialized: bool
    tool_cached: bool
    tool_validated: bool
    configuration: ModelRegistryConfiguration
    dependencies: ModelRegistryDependencies
    tool_info: ModelRegistryToolInfo
