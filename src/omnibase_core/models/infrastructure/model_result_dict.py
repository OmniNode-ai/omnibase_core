"""
Result Dictionary Model.

Clean Pydantic model for Result serialization following ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .model_cli_value import ModelCliValue
from .model_error_value import ModelErrorValue


class ModelResultDict(BaseModel):
    """
    Clean Pydantic model for Result serialization.

    Represents the dictionary structure when converting Results
    to/from dictionary format with proper type safety.
    """

    success: bool = Field(..., description="Whether the operation succeeded")
    value: ModelCliValue | None = Field(
        None,
        description="Success value (if success=True)",
    )
    error: ModelErrorValue | None = Field(
        None,
        description="Error value (if success=False)",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Type alias for dictionary-based data structures
ModelResultData = dict[str, ModelCliValue]  # Strongly-typed dict for common data


# Export for use
__all__ = ["ModelResultData", "ModelResultDict"]
