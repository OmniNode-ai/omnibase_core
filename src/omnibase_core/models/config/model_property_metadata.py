"""
Property metadata model for environment properties.

This module provides the ModelPropertyMetadata class for storing metadata
about individual properties in the environment property system.
"""

from pydantic import BaseModel, Field

from ...enums.enum_property_type import PropertyTypeEnum


class ModelPropertyMetadata(BaseModel):
    """Metadata for individual properties."""

    description: str | None = Field(None, description="Property description")
    source: str | None = Field(None, description="Source of the property")
    property_type: PropertyTypeEnum = Field(description="Type of the property")
    required: bool = Field(default=False, description="Whether property is required")
    validation_pattern: str | None = Field(
        None, description="Regex pattern for validation"
    )
    min_value: float | None = Field(None, description="Minimum value for numeric types")
    max_value: float | None = Field(None, description="Maximum value for numeric types")
    allowed_values: list[str] | None = Field(
        None, description="Allowed values for enum-like properties"
    )
