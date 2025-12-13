"""
ModelPermissionCustomFields: Custom extension fields for permissions.

This model provides structured custom fields for permissions without using Any types.
"""

from pydantic import BaseModel, Field


class ModelPermissionCustomFields(BaseModel):
    """Custom extension fields for permissions."""

    string_fields: dict[str, str] = Field(
        default_factory=dict,
        description="String-valued custom fields",
    )
    number_fields: dict[str, int] = Field(
        default_factory=dict,
        description="Integer-valued custom fields",
    )
    decimal_fields: dict[str, float] = Field(
        default_factory=dict,
        description="Float-valued custom fields",
    )
    boolean_fields: dict[str, bool] = Field(
        default_factory=dict,
        description="Boolean-valued custom fields",
    )
    list_fields: dict[str, list[str]] = Field(
        default_factory=dict,
        description="List-valued custom fields",
    )
