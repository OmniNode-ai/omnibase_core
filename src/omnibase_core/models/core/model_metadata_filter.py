"""Metadata-based custom filter model."""

from pydantic import Field

from omnibase_core.models.core.model_filter_operator import ModelFilterOperator

from .model_custom_filter_base import ModelCustomFilterBase


class ModelMetadataFilter(ModelCustomFilterBase):
    """Metadata-based custom filter."""

    filter_type: str = Field(default="metadata", description="Filter type identifier")
    metadata_key: str = Field(default=..., description="Metadata key to filter on")
    metadata_value: object = Field(default=..., description="Expected metadata value")
    operator: ModelFilterOperator = Field(
        default_factory=lambda: ModelFilterOperator(operator="eq", value=""),
        description="Comparison operator",
    )
