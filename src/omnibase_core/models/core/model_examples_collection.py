"""
Examples collection model.
"""

from typing import Any

from pydantic import BaseModel, Field

from .model_example import ModelExample
from .model_example_metadata import ModelExampleMetadata
from .model_generic_metadata import ModelGenericMetadata


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
            name=name,
            description=description,
            input_data=input_data,
            output_data=output_data,
            context=context,
            tags=tags or [],
            is_valid=True,
            validation_notes=None,
            created_at=None,
            updated_at=None,
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

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with strong typing preserved."""
        return {
            "examples": [example.model_dump() for example in self.examples],
            "metadata": self.metadata.model_dump() if self.metadata else None,
            "format": self.format,
            "schema_compliant": self.schema_compliant,
            "example_count": self.example_count(),
            "valid_example_count": self.valid_example_count(),
        }

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
                    raise ValueError(
                        msg,
                    )

                # Create ModelExample with proper validation
                try:
                    examples.append(ModelExample(**example_data))
                except Exception as e:
                    msg = f"Failed to create ModelExample: {e}"
                    raise ValueError(msg)

        # Create metadata if present
        metadata = None
        if data.get("metadata"):
            if isinstance(data["metadata"], dict):
                metadata = ModelExampleMetadata(**data["metadata"])
            else:
                msg = "Metadata must be a dictionary"
                raise ValueError(msg)

        return cls(
            examples=examples,
            metadata=metadata,
            format=data.get("format", "json"),
            schema_compliant=data.get("schema_compliant", True),
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
            name=name,
            description=None,
            input_data=input_data,
            output_data=output_data,
            context=None,
            tags=[],
            is_valid=True,
            validation_notes=None,
            created_at=None,
            updated_at=None,
        )
        return cls(examples=[example])
