"""
Example model for examples collection.

This module provides the ModelExample class for strongly typed
example data with comprehensive fields and validation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .model_example_context_data import ModelExampleContextData
from .model_example_data import ModelExampleInputData, ModelExampleOutputData


class ModelExample(BaseModel):
    """
    Strongly typed example model with comprehensive fields.

    Replaces placeholder implementation with proper validation and structure.
    """

    # Core identification
    example_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this example",
    )

    name: str = Field(
        ...,
        description="Name/title of the example",
        min_length=1,
    )

    description: str | None = Field(
        None,
        description="Detailed description of what this example demonstrates",
    )

    # Data fields
    input_data: ModelExampleInputData | None = Field(
        None,
        description="Input data for the example with type safety",
    )

    output_data: ModelExampleOutputData | None = Field(
        None,
        description="Expected output data for the example",
    )

    context: ModelExampleContextData | None = Field(
        None,
        description="Additional context information for the example",
    )

    # Metadata
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorizing and searching examples",
    )

    # Validation
    is_valid: bool = Field(
        default=True,
        description="Whether this example passes validation",
    )

    validation_notes: str | None = Field(
        None,
        description="Notes about validation status or issues",
    )

    # Timestamps
    created_at: datetime | None = Field(
        None,
        description="When this example was created",
    )

    updated_at: datetime | None = Field(
        None,
        description="When this example was last updated",
    )
