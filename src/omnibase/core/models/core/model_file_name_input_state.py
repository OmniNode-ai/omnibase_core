"""
Input state model for file name generation operations.
"""

from pydantic import Field

from omnibase.model.core.model_onex_base_state import ModelOnexInputState


class ModelFileNameInputState(ModelOnexInputState):
    """Input state for file name generation operations."""

    source_name: str = Field(..., description="Source name (class name, etc.)")
    file_extension: str = Field(".py", description="File extension")
