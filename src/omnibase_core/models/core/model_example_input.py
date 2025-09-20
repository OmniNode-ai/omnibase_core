"""
Example input model with strong typing.
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ModelExampleInput(BaseModel):
    """
    Structured input data for examples.

    Replaces dict[str, Any] with strongly typed input structure.
    """

    # Input identification
    input_id: UUID | None = Field(
        default=None,
        description="Unique identifier for this input"
    )

    # Core input data
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="The actual input data"
    )

    # Input metadata
    format: str | None = Field(
        default=None,
        description="Format of the input data (json, xml, text, etc.)"
    )

    encoding: str | None = Field(
        default=None,
        description="Encoding of the input data"
    )

    content_type: str | None = Field(
        default=None,
        description="MIME type or content type of the input"
    )

    # Input structure information
    schema_version: str | None = Field(
        default=None,
        description="Version of the input schema"
    )

    parameters: dict[str, Any] | None = Field(
        default=None,
        description="Additional parameters for the input"
    )

    # Validation and constraints
    constraints: dict[str, Any] | None = Field(
        default=None,
        description="Constraints or validation rules for this input"
    )

    # Input context
    context: dict[str, Any] | None = Field(
        default=None,
        description="Additional context information for the input"
    )

    # Processing hints
    processing_hints: dict[str, Any] | None = Field(
        default=None,
        description="Hints for how to process this input"
    )

    def get_data_field(self, key: str, default: Any = None) -> Any:
        """Get a field from the input data."""
        return self.data.get(key, default)

    def set_data_field(self, key: str, value: Any) -> None:
        """Set a field in the input data."""
        self.data[key] = value

    def has_data_field(self, key: str) -> bool:
        """Check if a field exists in the input data."""
        return key in self.data

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """Get a parameter value."""
        if self.parameters is None:
            return default
        return self.parameters.get(key, default)

    def set_parameter(self, key: str, value: Any) -> None:
        """Set a parameter value."""
        if self.parameters is None:
            self.parameters = {}
        self.parameters[key] = value

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelExampleInput":
        """Create from dictionary with validation."""
        if not isinstance(data, dict):
            raise ValueError(f"Expected dictionary, got {type(data)}")

        return cls(**data)

    @classmethod
    def create_simple(cls, data: dict[str, Any]) -> "ModelExampleInput":
        """Create a simple input with just data."""
        return cls(data=data)