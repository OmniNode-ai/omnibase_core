"""
ModelPermissionCustomFields: Custom extension fields for permissions.

This model provides structured custom fields for permissions without using Any types.
"""

from typing import Dict, List

from pydantic import BaseModel, Field


class ModelPermissionCustomFields(BaseModel):
    """Custom extension fields for permissions."""

    string_fields: Dict[str, str] = Field(
        default_factory=dict, description="String-valued custom fields"
    )
    number_fields: Dict[str, int] = Field(
        default_factory=dict, description="Integer-valued custom fields"
    )
    decimal_fields: Dict[str, float] = Field(
        default_factory=dict, description="Float-valued custom fields"
    )
    boolean_fields: Dict[str, bool] = Field(
        default_factory=dict, description="Boolean-valued custom fields"
    )
    list_fields: Dict[str, List[str]] = Field(
        default_factory=dict, description="List-valued custom fields"
    )
