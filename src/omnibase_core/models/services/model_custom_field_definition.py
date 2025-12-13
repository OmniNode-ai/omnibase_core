"""
CustomFieldDefinition model.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelCustomFieldDefinition(BaseModel):
    """Definition of a custom field."""

    field_name: str = Field(default=..., description="Field name")
    field_type: str = Field(
        default=...,
        description="Field type (string/number/boolean/date/json)",
    )
    required: bool = Field(default=False, description="Whether field is required")
    default_value: Any | None = Field(default=None, description="Default value")
    description: str | None = Field(default=None, description="Field description")
    validation_regex: str | None = Field(
        default=None,
        description="Validation regex pattern",
    )
