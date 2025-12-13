"""
Output Metadata Model

Strongly typed model for output metadata to replace Dict[str, Any] usage.
Follows ONEX canonical patterns with strict typing - no Any types allowed.
"""

from pydantic import BaseModel, Field


class ModelOutputMetadataItem(BaseModel):
    """Single output metadata item with strong typing."""

    key: str = Field(default=..., description="Metadata key")
    value: str | int | float | bool = Field(default=..., description="Metadata value")
    value_type: str = Field(
        default=...,
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
        default=None,
        description="Metadata category for organization",
    )
