"""
Examples collection model.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from ..metadata.model_generic_metadata import ModelGenericMetadata
from .model_examples_collection_summary import ModelExamplesCollectionSummary


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
    input_data: ModelGenericMetadata[Any] | None = Field(
        None,
        description="Input data for the example with type safety",
    )

    output_data: ModelGenericMetadata[Any] | None = Field(
        None,
        description="Expected output data for the example",
    )

    context: ModelGenericMetadata[Any] | None = Field(
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


class ModelExampleMetadata(BaseModel):
    """
    Metadata for example collections with enhanced structure.
    """

    title: str = Field(
        default="",
        description="Title for the examples collection",
    )

    description: str | None = Field(
        None,
        description="Description of the examples collection",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Tags for the entire collection",
    )

    difficulty: str = Field(
        default="beginner",
        description="Difficulty level (beginner, intermediate, advanced)",
        pattern="^(beginner|intermediate|advanced)$",
    )

    category: str | None = Field(
        None,
        description="Category this collection belongs to",
    )


from ..metadata.model_generic_metadata import ModelGenericMetadata


class ModelExamples(BaseModel):
    """
    Examples collection with typed fields.

    Strongly typed collection replacing Dict[str, Any] for examples fields
    with no magic strings or poorly typed dictionaries.
    """

    examples: list[ModelExample] = Field(
        default_factory=list,
        description="List of example data with strong typing",
    )

    metadata: ModelExampleMetadata | None = Field(
        default=None,
        description="Metadata about the examples collection",
    )

    format: str = Field(
        default="json",
        description="Format of examples (json/yaml/text)",
    )

    schema_compliant: bool = Field(
        default=True,
        description="Whether examples comply with schema",
    )

    def add_example(
        self,
        input_data: ModelGenericMetadata[Any],
        output_data: ModelGenericMetadata[Any] | None = None,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        context: ModelGenericMetadata[Any] | None = None,
    ) -> None:
        """Add a new example with full type safety."""
        example = ModelExample(
            name=name or f"Example_{len(self.examples) + 1}",
            description=description,
            input_data=input_data,
            output_data=output_data,
            context=context,
            tags=tags or [],
            is_valid=True,
            validation_notes=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.examples.append(example)

    def get_example(self, index: int = 0) -> ModelExample | None:
        """Get an example by index with bounds checking."""
        if 0 <= index < len(self.examples):
            return self.examples[index]
        return None

    def get_example_by_name(self, name: str) -> ModelExample | None:
        """Get an example by name with strong typing."""
        for example in self.examples:
            if example.name == name:
                return example
        return None

    def remove_example(self, index: int) -> bool:
        """Remove an example by index, return True if removed."""
        if 0 <= index < len(self.examples):
            del self.examples[index]
            return True
        return False

    def get_example_names(self) -> list[str]:
        """Get all example names."""
        return [example.name for example in self.examples if example.name]

    def get_valid_examples(self) -> list[ModelExample]:
        """Get only valid examples."""
        return [example for example in self.examples if example.is_valid]

    def example_count(self) -> int:
        """Get total number of examples."""
        return len(self.examples)

    def valid_example_count(self) -> int:
        """Get number of valid examples."""
        return len(self.get_valid_examples())

    def to_summary(self) -> ModelExamplesCollectionSummary:
        """Convert to clean, strongly-typed summary model."""
        from .model_examples_collection_summary import (
            ModelExampleMetadataSummary,
            ModelExampleSummary,
        )

        # Convert examples to summaries
        example_summaries = []
        for example in self.examples:
            example_summaries.append(
                ModelExampleSummary(
                    example_id=str(example.example_id),
                    name=example.name,
                    description=example.description,
                    is_valid=True,  # You can add validation logic here
                    input_data=(
                        example.input_data.model_dump() if example.input_data else None
                    ),
                    output_data=(
                        example.output_data.model_dump()
                        if example.output_data
                        else None
                    ),
                )
            )

        # Convert metadata
        metadata_summary = None
        if self.metadata:
            metadata_summary = ModelExampleMetadataSummary(
                created_at=(
                    str(self.metadata.created_at) if self.metadata.created_at else None
                ),
                updated_at=(
                    str(self.metadata.updated_at) if self.metadata.updated_at else None
                ),
                version=self.metadata.version,
                author=self.metadata.author,
                tags=self.metadata.tags or [],
                custom_fields=self.metadata.custom_fields or {},
            )

        return ModelExamplesCollectionSummary(
            examples=example_summaries,
            metadata=metadata_summary,
            format=self.format,
            schema_compliant=self.schema_compliant,
            example_count=self.example_count(),
            valid_example_count=self.valid_example_count(),
        )

    @classmethod
    def create_empty(cls) -> "ModelExamples":
        """Create an empty examples collection."""
        return cls()

    @classmethod
    def create_single_example(
        cls,
        input_data: ModelGenericMetadata[Any],
        output_data: ModelGenericMetadata[Any] | None = None,
        name: str | None = None,
    ) -> "ModelExamples":
        """Create collection with a single example."""
        example = ModelExample(
            name=name or "Single Example",
            description=None,
            input_data=input_data,
            output_data=output_data,
            context=None,
            tags=[],
            is_valid=True,
            validation_notes=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        return cls(examples=[example])
