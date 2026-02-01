"""Metadata filter model for vector queries.

This module provides the ModelVectorMetadataFilter class for defining
metadata-based filtering conditions in vector search operations.

Thread Safety:
    ModelVectorMetadataFilter instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_vector_filter_operator import (
    EnumVectorFilterOperator,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelVectorMetadataFilter(BaseModel):
    """A metadata filter condition for vector search queries.

    This model represents a single filter condition that can be applied
    to vector search operations to filter results based on metadata values.

    Attributes:
        field: The metadata field name to filter on.
        operator: The comparison operator to use.
        value: The value to compare against (single value or list for IN/NOT_IN).
            Uses ModelSchemaValue for type-safe value storage.

    Example:
        Exact match filter::

            from omnibase_core.models.vector import (
                ModelVectorMetadataFilter,
                EnumVectorFilterOperator,
            )
            from omnibase_core.models.common import ModelSchemaValue

            filter = ModelVectorMetadataFilter(
                field="category",
                operator=EnumVectorFilterOperator.EQ,
                value=ModelSchemaValue.from_value("science"),
            )

        Range filter::

            filter = ModelVectorMetadataFilter(
                field="year",
                operator=EnumVectorFilterOperator.GTE,
                value=ModelSchemaValue.from_value(2020),
            )

        List membership filter::

            filter = ModelVectorMetadataFilter(
                field="status",
                operator=EnumVectorFilterOperator.IN,
                value=ModelSchemaValue.from_value(["published", "reviewed"]),
            )
    """

    field: str = Field(
        ...,
        min_length=1,
        description="The metadata field name to filter on",
    )
    operator: EnumVectorFilterOperator = Field(
        ...,
        description="The comparison operator to use",
    )
    value: ModelSchemaValue = Field(
        ...,
        description="The value to compare against",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)


__all__ = ["ModelVectorMetadataFilter"]
