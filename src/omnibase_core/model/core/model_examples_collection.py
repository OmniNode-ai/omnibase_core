"""
Examples collection model.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from .model_example import ModelExample
from .model_example_metadata import ModelExampleMetadata


class ModelExamples(BaseModel):
    """
    Examples collection with typed fields.
    Replaces Dict[str, Any] for examples fields.
    """

    # Example entries - now properly typed as a list of ModelExample
    examples: list[ModelExample] = Field(
        default_factory=list,
        description="List of example data",
    )

    # Metadata for examples collection
    metadata: ModelExampleMetadata | None = Field(
        None,
        description="Metadata about the examples collection",
    )

    # Example format
    format: str = Field("json", description="Format of examples (json/yaml/text)")
    schema_compliant: bool = Field(
        True,
        description="Whether examples comply with schema",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        # Return just the examples list for backward compatibility
        if len(self.examples) == 1:
            return self.examples[0].dict(exclude_none=True)
        return {"examples": [ex.dict(exclude_none=True) for ex in self.examples]}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Optional["ModelExamples"]:
        """Create from dictionary for easy migration."""
        if data is None:
            return None

        # Handle different input formats
        if isinstance(data, list):
            examples = [
                (
                    ModelExample(**item)
                    if isinstance(item, dict)
                    else ModelExample(input_data=item)
                )
                for item in data
            ]
            return cls(examples=examples)
        if "examples" in data and isinstance(data["examples"], list):
            examples = [
                (
                    ModelExample(**item)
                    if isinstance(item, dict)
                    else ModelExample(input_data=item)
                )
                for item in data["examples"]
            ]
            return cls(
                examples=examples,
                metadata=data.get("metadata"),
                format=data.get("format", "json"),
                schema_compliant=data.get("schema_compliant", True),
            )
        # Single example as dict
        example = (
            ModelExample(**data)
            if all(k in data for k in ["input_data", "output_data"])
            else ModelExample(input_data=data)
        )
        return cls(examples=[example])

    def add_example(
        self,
        example: ModelExample | dict[str, Any],
        name: str | None = None,
    ):
        """Add a new example."""
        if isinstance(example, dict):
            example = (
                ModelExample(**example)
                if "input_data" in example
                else ModelExample(input_data=example)
            )

        if name and not example.name:
            example.name = name

        self.examples.append(example)

    def get_example(self, index: int = 0) -> ModelExample | None:
        """Get an example by index."""
        if 0 <= index < len(self.examples):
            return self.examples[index]
        return None
