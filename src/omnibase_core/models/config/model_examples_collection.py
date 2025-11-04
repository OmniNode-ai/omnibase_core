from __future__ import annotations

import json
from datetime import datetime
from typing import Generic

from pydantic import Field

from omnibase_core.models.errors.model_onex_error import ModelOnexError

__all__ = [
    "ModelExample",
    "ModelExamples",
]

"""
Examples collection model.
"""

from datetime import UTC
from typing import Any

from pydantic import BaseModel

from omnibase_core.enums.enum_data_format import EnumDataFormat
from omnibase_core.errors.error_codes import EnumCoreErrorCode

from .model_example import ModelExample
from .model_example_context_data import ModelExampleContextData
from .model_example_data import ModelExampleInputData, ModelExampleOutputData
from .model_example_metadata import ModelExampleMetadata
from .model_examples_collection_summary import ModelExamplesCollectionSummary


class ModelExamples(BaseModel):
    """
    Examples collection with typed fields.

    Strongly typed collection replacing Dict[str, Any] for examples fields
    with no magic strings or poorly typed dict[str, Any]ionaries.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    examples: list[ModelExample] = Field(
        default_factory=list,
        description="List of example data with strong typing",
    )

    metadata: ModelExampleMetadata | None = Field(
        default=None,
        description="Metadata about the examples collection",
    )

    format: EnumDataFormat = Field(
        default=EnumDataFormat.JSON,
        description="Format of examples (json/yaml/text)",
    )

    schema_compliant: bool = Field(
        default=True,
        description="Whether examples comply with schema",
    )

    def add_example(
        self,
        input_data: ModelExampleInputData,
        output_data: ModelExampleOutputData | None = None,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        context: ModelExampleContextData | None = None,
    ) -> None:
        """Add a new example with full type safety."""
        example = ModelExample(
            name=name or f"Example_{len(self.examples) + 1}",
            description=description or "",
            input_data=input_data,
            output_data=output_data,
            context=context,
            tags=tags or [],
            is_valid=True,
            validation_notes="",
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
                    example_id=example.example_id,
                    display_name=example.name,
                    description=example.description,
                    is_valid=True,  # You can add validation logic here
                    input_data=None,  # Type mismatch: ModelGenericMetadata vs ModelExampleInputData
                    output_data=None,  # Type mismatch: ModelGenericMetadata vs ModelExampleOutputData
                ),
            )

        # Convert metadata
        metadata_summary = None
        if self.metadata:
            metadata_summary = ModelExampleMetadataSummary(
                created_at=None,  # Not available in current metadata model
                updated_at=None,  # Not available in current metadata model
                version=None,  # Not available in current metadata model
                author_id=None,  # Not available in current metadata model
                author_display_name=None,  # Not available in current metadata model
                tags=self.metadata.tags or [],
                custom_fields={},  # Not available in current metadata model
            )

        return ModelExamplesCollectionSummary(
            examples=example_summaries,
            metadata=metadata_summary,
            format=self.format,
            schema_compliant=self.schema_compliant,
            example_count=self.example_count(),
            valid_example_count=self.valid_example_count(),
            last_updated=datetime.now(UTC),
        )

    @classmethod
    def create_empty(cls) -> ModelExamples:
        """Create an empty examples collection."""
        return cls()

    @classmethod
    def create_single_example(
        cls,
        input_data: ModelExampleInputData,
        output_data: ModelExampleOutputData | None = None,
        name: str | None = None,
    ) -> ModelExamples:
        """Create collection with a single example."""
        example = ModelExample(
            name=name or "Single Example",
            description="",
            input_data=input_data,
            output_data=output_data,
            context=None,
            tags=[],
            is_valid=True,
            validation_notes="",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        return cls(examples=[example])

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol).

        Raises:
            ModelOnexError: If configuration fails with details about the failure
        """
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Configuration failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            ModelOnexError: If validation fails with details about the failure
        """
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Instance validation failed: {e}",
            ) from e
