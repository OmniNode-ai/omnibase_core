"""
Input state model for word splitting operations.
"""

from pydantic import Field

from omnibase_core.models.core.model_onex_base_state import ModelOnexInputState


class ModelWordSplitInputState(ModelOnexInputState):
    """Input state for word splitting operations."""

    input_string: str = Field(default=..., description="String to split into words")
    preserve_acronyms: bool = Field(
        default=True, description="Whether to preserve acronyms"
    )
