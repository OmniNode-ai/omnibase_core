"""
Input state model for file name generation operations.
"""

from pydantic import Field

from omnibase_core.models.core.model_onex_base_state import ModelOnexInputState


class ModelFileNameInputState(ModelOnexInputState):
    """Input state for file name generation operations."""

    source_name: str = Field(default=..., description="Source name (class name, etc.)")
    file_extension: str = Field(default=".py", description="File extension")
