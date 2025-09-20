"""
Examples collection summary model.

Clean, strongly-typed replacement for the horrible union return type.
Follows ONEX one-model-per-file naming conventions.
"""

from typing import Any

from pydantic import BaseModel, Field

from .model_example_data import ModelExampleInputData, ModelExampleOutputData


class ModelExampleSummary(BaseModel):
    """Clean model for individual example summary data."""

    example_id: str = Field(..., description="Example identifier")
    name: str = Field(..., description="Example name")
    description: str | None = Field(None, description="Example description")
    is_valid: bool = Field(default=True, description="Whether example is valid")
    input_data: ModelExampleInputData | None = Field(None, description="Input data")
    output_data: ModelExampleOutputData | None = Field(None, description="Output data")


class ModelExampleMetadataSummary(BaseModel):
    """Clean model for metadata summary."""

    created_at: str | None = Field(None, description="Creation timestamp")
    updated_at: str | None = Field(None, description="Update timestamp")
    version: str | None = Field(None, description="Metadata version")
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

    @classmethod
    def from_legacy_dict(
        cls,
        data: dict[str, str | int | bool | list[dict[str, str | int | bool]] | None],
    ) -> "ModelExamplesCollectionSummary":
        """
        Create from legacy dict data for migration.

        This method helps migrate from the horrible union type to clean model.
        """
        # Extract examples data
        examples_data = data.get("examples", [])
        examples = []

        if isinstance(examples_data, list):
            for i, example_dict in enumerate(examples_data):
                if isinstance(example_dict, dict):
                    examples.append(
                        ModelExampleSummary(
                            example_id=example_dict.get("example_id", f"example_{i}"),
                            name=example_dict.get("name", f"Example {i}"),
                            description=example_dict.get("description"),
                            is_valid=example_dict.get("is_valid", True),
                            input_data=example_dict.get("input_data"),
                            output_data=example_dict.get("output_data"),
                        )
                    )

        # Extract metadata
        metadata_data = data.get("metadata")
        metadata = None
        if isinstance(metadata_data, dict):
            metadata = ModelExampleMetadataSummary(
                created_at=metadata_data.get("created_at"),
                updated_at=metadata_data.get("updated_at"),
                version=metadata_data.get("version"),
                author=metadata_data.get("author"),
                tags=metadata_data.get("tags", []),
                custom_fields=metadata_data.get("custom_fields", {}),
            )

        return cls(
            examples=examples,
            metadata=metadata,
            format=str(data.get("format", "json")),
            schema_compliant=bool(data.get("schema_compliant", True)),
            example_count=int(data.get("example_count", len(examples))),
            valid_example_count=int(data.get("valid_example_count", len(examples))),
        )


# Export the models
__all__ = [
    "ModelExamplesCollectionSummary",
    "ModelExampleSummary",
    "ModelExampleMetadataSummary",
]
