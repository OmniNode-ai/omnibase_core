"""
Examples collection summary model.

Clean, strongly-typed replacement for the horrible union return type.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ...enums.enum_data_format import EnumDataFormat
from .model_example_metadata_summary import ModelExampleMetadataSummary
from .model_example_summary import ModelExampleSummary


class ModelExamplesCollectionSummary(BaseModel):
    """
    Clean, strongly-typed model replacing the horrible union return type.

    Eliminates: dict[str, list[dict[str, Any]] | dict[str, Any] | None | int | bool]

    With proper structured data using specific field types.
    """

    examples: list[ModelExampleSummary] = Field(
        default_factory=list,
        description="List of example summaries",
    )

    metadata: ModelExampleMetadataSummary | None = Field(
        None,
        description="Collection metadata summary",
    )

    format: EnumDataFormat = Field(
        default=EnumDataFormat.JSON,
        description="Collection format",
    )

    schema_compliant: bool = Field(
        default=True,
        description="Whether collection is schema compliant",
    )

    example_count: int = Field(default=0, description="Total number of examples")

    valid_example_count: int = Field(default=0, description="Number of valid examples")

    # Statistics
    completion_rate: float = Field(
        default=0.0,
        description="Percentage of valid examples",
    )

    last_updated: str | None = Field(None, description="Last update timestamp")

    def model_post_init(self, __context: Any) -> None:
        """Calculate completion rate after initialization."""
        if self.example_count > 0:
            self.completion_rate = (self.valid_example_count / self.example_count) * 100
        else:
            self.completion_rate = 0.0


# Export the models
__all__ = [
    "ModelExampleMetadataSummary",
    "ModelExampleSummary",
    "ModelExamplesCollectionSummary",
]
