"""
Examples collection model with strong typing and UUID support.

Enhanced with generic collection patterns for type-safe operations
and reusable collection behaviors.
"""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from ...enums.enum_example_category import EnumExampleCategory
from ...enums.enum_example_validation_status import EnumExampleValidationStatus
from .model_example import ModelExample
from .model_example_input import ModelExampleInput
from .model_example_metadata import ModelExampleMetadata
from .model_example_output import ModelExampleOutput
from .model_generic_collection import ModelIdentifiableCollection, Identifiable


class ModelExamples(ModelIdentifiableCollection[ModelExample]):
    """
    Examples collection with strong typing and UUID support.

    Strongly typed collection that replaces Dict[str, Any] for examples fields
    with proper models, UUIDs, and enum-based categorization.

    Inherits from ModelIdentifiableCollection to provide type-safe collection
    operations with ID-based access patterns.
    """

    # Collection metadata
    example_metadata: ModelExampleMetadata | None = Field(
        default=None,
        description="Metadata about the examples collection"
    )

    # Collection properties
    format: str = Field(
        default="json",
        description="Format of examples (json/yaml/text)"
    )

    schema_compliant: bool = Field(
        default=True,
        description="Whether examples comply with schema"
    )

    # Collection versioning
    version: str | None = Field(
        default=None,
        description="Version of the collection"
    )

    # Collection statistics (computed)
    @property
    def example_count(self) -> int:
        """Get total number of examples."""
        return len(self.items)

    @property
    def valid_example_count(self) -> int:
        """Get number of valid examples."""
        return len([ex for ex in self.items if ex.is_valid()])

    @property
    def pending_example_count(self) -> int:
        """Get number of examples pending validation."""
        return len([ex for ex in self.items if ex.is_pending_validation()])

    def add_example(
        self,
        input_data: ModelExampleInput | None = None,
        output_data: ModelExampleOutput | None = None,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        category: EnumExampleCategory | None = None,
        context: dict[str, Any] | None = None,
        author_id: UUID | None = None,
        author_name: str | None = None,
    ) -> ModelExample:
        """Add a new example with full type safety."""
        example = ModelExample(
            name=name,
            description=description,
            input_data=input_data,
            output_data=output_data,
            category=category,
            tags=tags or [],
            context=context,
            validation_status=EnumExampleValidationStatus.PENDING,
            author_id=author_id,
            author_name=author_name,
        )
        self.add(example)  # Use generic collection's add method
        return example

    def add_simple_example(
        self,
        name: str,
        input_dict: dict[str, Any] | None = None,
        output_dict: dict[str, Any] | None = None,
        category: EnumExampleCategory | None = None
    ) -> ModelExample:
        """Add a simple example from dictionaries."""
        input_data = ModelExampleInput.create_simple(input_dict or {}) if input_dict else None
        output_data = ModelExampleOutput.create_simple(output_dict or {}) if output_dict else None

        return self.add_example(
            name=name,
            input_data=input_data,
            output_data=output_data,
            category=category
        )

    def get_example(self, index: int = 0) -> ModelExample | None:
        """Get an example by index with bounds checking."""
        return self.get_by_index(index)  # Use generic collection method

    def get_example_by_id(self, example_id: UUID) -> ModelExample | None:
        """Get an example by its UUID."""
        return self.get_by_id(example_id)  # Use generic collection method

    def get_example_by_name(self, name: str) -> ModelExample | None:
        """Get an example by name with strong typing."""
        for example in self.items:
            if example.name == name:
                return example
        return None

    def get_examples_by_category(self, category: EnumExampleCategory) -> list[ModelExample]:
        """Get all examples in a specific category."""
        return [ex for ex in self.items if ex.category == category]

    def get_examples_by_validation_status(
        self,
        status: EnumExampleValidationStatus
    ) -> list[ModelExample]:
        """Get all examples with a specific validation status."""
        return [ex for ex in self.items if ex.validation_status == status]

    def get_examples_by_author(self, author_id: UUID) -> list[ModelExample]:
        """Get all examples by a specific author."""
        return [ex for ex in self.items if ex.author_id == author_id]

    def get_examples_with_tag(self, tag: str) -> list[ModelExample]:
        """Get all examples that have a specific tag."""
        return [ex for ex in self.items if tag in ex.tags]

    def remove_example(self, index: int) -> bool:
        """Remove an example by index, return True if removed."""
        if 0 <= index < len(self.items):
            del self.items[index]
            return True
        return False

    def remove_example_by_id(self, example_id: UUID) -> bool:
        """Remove an example by its UUID."""
        return self.remove_by_id(example_id)  # Use generic collection method

    def get_example_names(self) -> list[str]:
        """Get all example names."""
        return [example.name for example in self.items if example.name]

    def get_valid_examples(self) -> list[ModelExample]:
        """Get only valid examples."""
        return [example for example in self.items if example.is_valid()]

    def get_complete_examples(self) -> list[ModelExample]:
        """Get examples that have both input and output data."""
        return [example for example in self.items if example.is_complete()]

    def validate_all_examples(self) -> dict[str, int]:
        """Get validation statistics for all examples."""
        stats = {}
        for status in EnumExampleValidationStatus:
            stats[status.value] = len(self.get_examples_by_validation_status(status))
        return stats

    def get_categories_used(self) -> list[EnumExampleCategory]:
        """Get all categories used in this collection."""
        categories = set()
        for example in self.items:
            if example.category:
                categories.add(example.category)
        return list(categories)

    def get_all_tags(self) -> list[str]:
        """Get all unique tags used in examples."""
        tags = set()
        for example in self.items:
            tags.update(example.tags)
        return list(tags)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with strong typing preserved."""
        base_dict = super().to_dict()  # Get base collection dict
        base_dict.update({
            "examples": [example.to_dict() for example in self.items],
            "metadata": self.example_metadata.to_dict() if self.example_metadata else None,
            "format": self.format,
            "schema_compliant": self.schema_compliant,
            "version": self.version,
            "statistics": {
                "example_count": self.example_count,
                "valid_example_count": self.valid_example_count,
                "pending_example_count": self.pending_example_count,
                "categories_used": [cat.value for cat in self.get_categories_used()],
                "unique_tags": self.get_all_tags(),
            }
        })
        return base_dict

    @classmethod
    def from_dict(cls, data: Any) -> "ModelExamples":
        """Create from dictionary with strict type validation."""
        if not isinstance(data, dict):
            msg = f"Expected dictionary, got {type(data)}"
            raise ValueError(msg)

        examples: list[ModelExample] = []

        # Handle different input formats with validation
        if "examples" in data and isinstance(data["examples"], list):
            for example_data in data["examples"]:
                if not isinstance(example_data, dict):
                    msg = f"Example data must be a dictionary, got {type(example_data)}"
                    raise ValueError(msg)

                # Create ModelExample with proper validation
                try:
                    examples.append(ModelExample.from_dict(example_data))
                except Exception as e:
                    msg = f"Failed to create ModelExample: {e}"
                    raise ValueError(msg) from e

        # Create metadata if present
        metadata = None
        if data.get("metadata"):
            if isinstance(data["metadata"], dict):
                metadata = ModelExampleMetadata.from_dict(data["metadata"])
            else:
                msg = "Metadata must be a dictionary"
                raise ValueError(msg)

        # Parse collection_id if present
        collection_id = None
        if data.get("collection_id"):
            try:
                collection_id = UUID(data["collection_id"])
            except (ValueError, TypeError) as e:
                msg = f"Invalid collection_id format: {e}"
                raise ValueError(msg) from e

        return cls(
            collection_id=collection_id or uuid4(),
            items=examples,  # Use items instead of examples
            example_metadata=metadata,
            format=data.get("format", "json"),
            schema_compliant=data.get("schema_compliant", True),
            version=data.get("version"),
        )

    @classmethod
    def create_empty(cls, collection_id: UUID | None = None) -> "ModelExamples":
        """Create an empty examples collection."""
        return cls(collection_id=collection_id or uuid4())

    @classmethod
    def create_with_metadata(
        cls,
        metadata: ModelExampleMetadata,
        collection_id: UUID | None = None
    ) -> "ModelExamples":
        """Create collection with metadata."""
        return cls(collection_id=collection_id or uuid4(), example_metadata=metadata)

    @classmethod
    def create_single_example(
        cls,
        input_data: ModelExampleInput | None = None,
        output_data: ModelExampleOutput | None = None,
        name: str | None = None,
        category: EnumExampleCategory | None = None,
        collection_id: UUID | None = None
    ) -> "ModelExamples":
        """Create collection with a single example."""
        collection = cls(collection_id=collection_id or uuid4())
        collection.add_example(
            input_data=input_data,
            output_data=output_data,
            name=name,
            category=category
        )
        return collection