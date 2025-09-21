"""
Example summary model.

This module provides the ModelExampleSummary class for clean
individual example summary data following ONEX naming conventions.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .model_example_data import ModelExampleInputData, ModelExampleOutputData


class ModelExampleSummary(BaseModel):
    """Clean model for individual example summary data."""

    example_id: UUID = Field(default_factory=uuid4, description="Example identifier")

    # Entity reference - UUID-based with display name
    entity_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the example entity"
    )
    display_name: str = Field(..., description="Example display name")

    description: str | None = Field(None, description="Example description")
    is_valid: bool = Field(default=True, description="Whether example is valid")
    input_data: ModelExampleInputData | None = Field(None, description="Input data")
    output_data: ModelExampleOutputData | None = Field(None, description="Output data")

    @classmethod
    def create_legacy(
        cls,
        name: str,
        description: str | None = None,
        is_valid: bool = True,
        input_data: ModelExampleInputData | None = None,
        output_data: ModelExampleOutputData | None = None,
    ) -> ModelExampleSummary:
        """Create example summary with legacy name parameter for backward compatibility."""
        return cls(
            display_name=name,
            description=description,
            is_valid=is_valid,
            input_data=input_data,
            output_data=output_data,
        )

    @property
    def name(self) -> str:
        """Legacy property for backward compatibility."""
        return self.display_name
