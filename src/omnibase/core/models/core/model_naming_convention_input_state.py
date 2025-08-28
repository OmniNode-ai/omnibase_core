"""
Input state model for naming convention conversion operations.
"""

from typing import Optional

from pydantic import Field

from omnibase.model.core.model_onex_base_state import ModelOnexInputState


class ModelNamingConventionInputState(ModelOnexInputState):
    """Input state for naming convention conversion operations."""

    input_string: str = Field(..., description="String to convert")
    target_convention: str = Field(
        ..., description="Target convention (pascal_case, snake_case, etc.)"
    )
    source_convention: Optional[str] = Field(None, description="Source convention hint")
