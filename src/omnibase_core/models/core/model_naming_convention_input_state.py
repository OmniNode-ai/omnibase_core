"""
Input state model for naming convention conversion operations.
"""

from pydantic import Field

from omnibase_core.models.core.model_onex_base_state import ModelOnexInputState


class ModelNamingConventionInputState(ModelOnexInputState):
    """Input state for naming convention conversion operations."""

    input_string: str = Field(default=..., description="String to convert")
    target_convention: str = Field(
        default=...,
        description="Target convention (pascal_case, snake_case, etc.)",
    )
    source_convention: str | None = Field(
        default=None, description="Source convention hint"
    )
