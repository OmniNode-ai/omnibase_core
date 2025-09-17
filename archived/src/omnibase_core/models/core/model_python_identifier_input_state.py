"""
Input state model for Python identifier validation operations.
"""

from pydantic import Field

from omnibase_core.models.core.model_onex_base_state import ModelOnexInputState


class ModelPythonIdentifierInputState(ModelOnexInputState):
    """Input state for Python identifier validation operations."""

    identifier: str = Field(..., description="Identifier to validate/sanitize")
    sanitize: bool = Field(False, description="Whether to sanitize invalid identifiers")
