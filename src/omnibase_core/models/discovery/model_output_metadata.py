import json
from typing import Any, Dict

from pydantic import Field

from .model_outputmetadata import ModelOutputMetadata

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
