"""Complex composite filter model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import Field

from .model_custom_filter_base import ModelCustomFilterBase

if TYPE_CHECKING:
    from .model_datetime_filter import ModelDateTimeFilter
    from .model_list_filter import ModelListFilter
    from .model_metadata_filter import ModelMetadataFilter
    from .model_numeric_filter import ModelNumericFilter
    from .model_status_filter import ModelStatusFilter
    from .model_string_filter import ModelStringFilter


class ModelComplexFilter(ModelCustomFilterBase):
    """Complex composite filter."""

    filter_type: str = Field(default="complex", description="Filter type identifier")
    sub_filters: list[
        # union-ok: Composite filter pattern legitimately needs union of all filter types
        ModelStringFilter
        | ModelNumericFilter
        | ModelDateTimeFilter
        | ModelListFilter
        | ModelMetadataFilter
        | ModelStatusFilter
    ] = Field(default=..., description="List of sub-filters to apply")
    logic: str = Field(default="AND", description="Logical operator (AND/OR)")
    negate: bool = Field(default=False, description="Negate the entire filter result")
