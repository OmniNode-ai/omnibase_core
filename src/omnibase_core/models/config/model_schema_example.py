"""
Schema example model.

Type-safe model for extracting examples from YAML schema files,
replacing dict[str, Any] return types with structured models.
"""

from __future__ import annotations

from typing import TypeVar, overload

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_data_type import EnumDataType
from omnibase_core.models.core.model_custom_properties import ModelCustomProperties
from omnibase_core.models.metadata.model_semver import ModelSemVer

T = TypeVar("T")


class ModelSchemaExample(BaseModel):
    """
    Type-safe model for schema examples.

    Replaces dict[str, Any] returns from extract_example_from_schema
    with properly structured and validated data.
    """

    # Core example data - using existing typed properties pattern
    example_data: ModelCustomProperties = Field(
        default_factory=ModelCustomProperties,
        description="Type-safe example data from schema",
    )

    # Metadata about the example
    example_index: int = Field(
        description="Index of this example in the schema examples array",
    )

    schema_path: str = Field(
        description="Path to the schema file this example was extracted from",
    )

    # Optional validation info
    data_format: EnumDataType = Field(
        default=EnumDataType.YAML,
        description="Format of the example data",
    )

    schema_version: ModelSemVer | None = Field(
        None,
        description="Schema version if available",
    )

    is_validated: bool = Field(
        default=False,
        description="Whether example has been validated against schema",
    )

    def has_data(self) -> bool:
        """Check if example contains any data."""
        return not self.example_data.is_empty()

    def get_value(self, key: str, default: T) -> T:
        """Get typed value with proper default handling."""
        value = self.example_data.get_custom_value(key)
        return value if value is not None else default

    def set_value(self, key: str, value: T) -> None:
        """Set typed value in example data."""
        self.example_data.set_custom_value(key, value)

    def get_all_keys(self) -> list[str]:
        """Get all keys from example data."""
        return list(self.example_data.get_all_custom_fields().keys())


# Export the model
__all__ = ["ModelSchemaExample"]
