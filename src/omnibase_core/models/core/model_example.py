from pydantic import Field

"""
Example model.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ModelExample(BaseModel):
    """
    Individual example with typed fields.
    """

    # Example identification
    name: str | None = Field(default=None, description="Example name")
    description: str | None = Field(default=None, description="Example description")

    # Example data - using a more structured approach
    input_data: dict[str, Any] | None = Field(
        default=None, description="Example input data"
    )
    output_data: dict[str, Any] | None = Field(
        default=None,
        description="Example output data",
    )

    # Additional context
    context: dict[str, Any] | None = Field(
        default=None,
        description="Additional context for the example",
    )
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")

    # Validation info
    is_valid: bool = Field(default=True, description="Whether this example is valid")
    validation_notes: str | None = Field(
        default=None, description="Notes about validation"
    )

    # Timestamps
    created_at: datetime | None = Field(
        default=None,
        description="When the example was created",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="When the example was last updated",
    )
