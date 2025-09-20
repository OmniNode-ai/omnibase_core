"""
Examples collection summary model.

Clean, strongly-typed replacement for the horrible union return type.
Follows ONEX one-model-per-file naming conventions.
"""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from ..metadata.model_semver import ModelSemVer
from .model_example_data import ModelExampleInputData, ModelExampleOutputData


class ModelExampleSummary(BaseModel):
    """Clean model for individual example summary data."""

    example_id: UUID = Field(default_factory=uuid4, description="Example identifier")
    name: str = Field(..., description="Example name")
    description: str | None = Field(None, description="Example description")
    is_valid: bool = Field(default=True, description="Whether example is valid")
    input_data: ModelExampleInputData | None = Field(None, description="Input data")
    output_data: ModelExampleOutputData | None = Field(None, description="Output data")


class ModelExampleMetadataSummary(BaseModel):
    """Clean model for metadata summary."""

    created_at: str | None = Field(None, description="Creation timestamp")
    updated_at: str | None = Field(None, description="Update timestamp")
    version: ModelSemVer | None = Field(None, description="Metadata version")
    author: str | None = Field(None, description="Author information")
    tags: list[str] = Field(default_factory=list, description="Associated tags")
    custom_fields: dict[str, str | int | bool | float] = Field(
        default_factory=dict, description="Custom metadata fields with basic types only"
    )


class ModelExamplesCollectionSummary(BaseModel):
    """
    Clean, strongly-typed model replacing the horrible union return type.

    Eliminates: dict[str, list[dict[str, Any]] | dict[str, Any] | None | int | bool]

    With proper structured data using specific field types.
    """

    examples: list[ModelExampleSummary] = Field(
        default_factory=list, description="List of example summaries"
    )

    metadata: ModelExampleMetadataSummary | None = Field(
        None, description="Collection metadata summary"
    )

    format: str = Field(default="json", description="Collection format")

    schema_compliant: bool = Field(
        default=True, description="Whether collection is schema compliant"
    )

    example_count: int = Field(default=0, description="Total number of examples")

    valid_example_count: int = Field(default=0, description="Number of valid examples")

    # Statistics
    completion_rate: float = Field(
        default=0.0, description="Percentage of valid examples"
    )

    last_updated: str | None = Field(None, description="Last update timestamp")

    def model_post_init(self, __context: Any) -> None:
        """Calculate completion rate after initialization."""
        if self.example_count > 0:
            self.completion_rate = (self.valid_example_count / self.example_count) * 100
        else:
            self.completion_rate = 0.0
