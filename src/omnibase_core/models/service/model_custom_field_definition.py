import json

from pydantic import Field

"""
CustomFieldDefinition model.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelCustomFieldDefinition(BaseModel):
    """Definition of a custom field."""

    field_name: str = Field(..., description="Field name")
    field_type: str = Field(
        ...,
        description="Field type (string/number/boolean/date/json)",
    )
    required: bool = Field(False, description="Whether field is required")
    default_value: Any | None = Field(None, description="Default value")
    description: str | None = Field(None, description="Field description")
    validation_regex: str | None = Field(
        None,
        description="Validation regex pattern",
    )
