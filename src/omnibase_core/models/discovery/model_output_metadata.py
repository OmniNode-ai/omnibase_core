"""
Output Metadata Model

Strongly typed model for output metadata to replace Dict[str, Any] usage.
Follows ONEX canonical patterns with zero tolerance for Any types.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelOutputMetadataItem(BaseModel):
    """Single output metadata item with strong typing."""

    key: str = Field(..., description="Metadata key")
    value: str | int | float | bool = Field(..., description="Metadata value")
    value_type: str = Field(
        ...,
        description="Value type",
        json_schema_extra={
            "enum": [
                "string",
                "integer",
                "float",
                "boolean",
                "timestamp",
                "url",
                "path",
            ],
        },
    )
    category: str | None = Field(
        None,
        description="Metadata category for organization",
    )


class ModelOutputMetadata(BaseModel):
    """Output metadata container with strong typing."""

    items: list[ModelOutputMetadataItem] = Field(
        default_factory=list,
        description="List of typed output metadata items",
    )
    execution_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When metadata was created",
    )

    def get_metadata_dict(self) -> dict[str, str | int | float | bool]:
        """Convert to dictionary format for current standards."""
        return {item.key: item.value for item in self.items}

    @classmethod
    def from_dict(
        cls,
        metadata_dict: dict[str, str | int | float | bool],
    ) -> "ModelOutputMetadata":
        """Create from dictionary with type inference."""
        items = []
        for key, value in metadata_dict.items():
            if isinstance(value, str):
                value_type = "string"
            elif isinstance(value, int):
                value_type = "integer"
            elif isinstance(value, float):
                value_type = "float"
            elif isinstance(value, bool):
                value_type = "boolean"
            else:
                # Fallback to string representation
                value_type = "string"
                value = str(value)

            items.append(
                ModelOutputMetadataItem(key=key, value=value, value_type=value_type),
            )

        return cls(items=items)
