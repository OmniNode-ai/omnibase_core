"""
Result dictionary model.

Clean Pydantic model for Result serialization.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .model_cli_value import ModelCliValue


class ModelResultDict(BaseModel):
    """
    Clean Pydantic model for Result serialization.

    Represents the dictionary structure when converting Results
    to/from dictionary format with proper type safety.
    """

    success: bool = Field(..., description="Whether the operation succeeded")
    value: ModelCliValue | None = Field(
        None, description="Success value (if success=True)"
    )
    error: str | Exception | None = Field(
        None, description="Error value (if success=False)"
    )

    model_config = {"arbitrary_types_allowed": True}


# Type alias for dictionary-based data structures
ModelResultData = dict[str, ModelCliValue]  # Strongly-typed dict for common data


# Export for use
__all__ = ["ModelResultDict", "ModelResultData"]
