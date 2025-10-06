"""
Input state model for class name generation operations.
"""

from pydantic import Field

from omnibase_core.models.core.model_onex_base_state import ModelOnexInputState


class ModelClassNameInputState(ModelOnexInputState):
    """Input state for class name generation operations."""

    base_name: str = Field(
        default=..., description="Base name to convert to class name"
    )
    add_model_prefix: bool = Field(
        default=False, description="Whether to add 'Model' prefix"
    )
    class_type: str | None = Field(
        default=None,
        description="Type hint for naming (tool, model, enum)",
    )
