"""
Input state model for class name generation operations.
"""

from typing import Optional

from pydantic import Field

from omnibase.model.core.model_onex_base_state import ModelOnexInputState


class ModelClassNameInputState(ModelOnexInputState):
    """Input state for class name generation operations."""

    base_name: str = Field(..., description="Base name to convert to class name")
    add_model_prefix: bool = Field(False, description="Whether to add 'Model' prefix")
    class_type: Optional[str] = Field(
        None, description="Type hint for naming (tool, model, enum)"
    )
