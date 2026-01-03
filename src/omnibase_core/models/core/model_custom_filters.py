"""Collection of custom filters model."""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

from .model_complex_filter import ModelComplexFilter
from .model_datetime_filter import ModelDateTimeFilter
from .model_list_filter import ModelListFilter
from .model_metadata_filter import ModelMetadataFilter
from .model_numeric_filter import ModelNumericFilter
from .model_status_filter import ModelStatusFilter
from .model_string_filter import ModelStringFilter


class ModelCustomFilters(BaseModel):
    """
    Collection of custom filters.

    Replaces Dict[str, Any] for custom_filters fields with typed filters.
    """

    # union-ok: discriminated_model_union - All filter types share filter_type discriminator field
    filters: dict[
        str,
        ModelStringFilter
        | ModelNumericFilter
        | ModelDateTimeFilter
        | ModelListFilter
        | ModelMetadataFilter
        | ModelStatusFilter
        | ModelComplexFilter,
    ] = Field(default_factory=dict, description="Named custom filters")

    def add_string_filter(self, name: str, pattern: str, **kwargs: Any) -> None:
        """Add a string filter."""
        self.filters[name] = ModelStringFilter(pattern=pattern, **kwargs)

    def add_numeric_filter(self, name: str, **kwargs: Any) -> None:
        """Add a numeric filter."""
        self.filters[name] = ModelNumericFilter(**kwargs)

    def add_datetime_filter(self, name: str, **kwargs: Any) -> None:
        """Add a datetime filter."""
        self.filters[name] = ModelDateTimeFilter(**kwargs)

    def add_list_filter(
        self,
        name: str,
        values: list[object] | list[ModelSchemaValue],
        **kwargs: Any,
    ) -> None:
        """Add a list filter.

        Values are automatically converted to ModelSchemaValue for type safety.
        """
        self.filters[name] = ModelListFilter(
            values=cast(list[ModelSchemaValue], values), **kwargs
        )

    def add_metadata_filter(
        self, name: str, key: str, value: object, **kwargs: Any
    ) -> None:
        """Add a metadata filter."""
        self.filters[name] = ModelMetadataFilter(
            metadata_key=key,
            metadata_value=value,
            **kwargs,
        )

    def add_status_filter(self, name: str, allowed: list[str], **kwargs: Any) -> None:
        """Add a status filter."""
        self.filters[name] = ModelStatusFilter(allowed_statuses=allowed, **kwargs)

    # union-ok: discriminated_model_union - All filter types share filter_type discriminator field
    def get_filter(
        self, name: str
    ) -> (
        ModelStringFilter
        | ModelNumericFilter
        | ModelDateTimeFilter
        | ModelListFilter
        | ModelMetadataFilter
        | ModelStatusFilter
        | ModelComplexFilter
        | None
    ):
        """Get a filter by name."""
        return self.filters.get(name)

    def remove_filter(self, name: str) -> None:
        """Remove a filter by name."""
        self.filters.pop(name, None)

    def to_dict(self) -> SerializedDict:
        """Convert to dictionary (for current standards)."""
        # Custom transformation logic for filters dictionary
        return {name: filter_obj.to_dict() for name, filter_obj in self.filters.items()}

    @classmethod
    def from_dict(cls, data: SerializedDict) -> ModelCustomFilters:
        """Create from dictionary (for migration)."""
        # union-ok: discriminated_model_union - All filter types share filter_type discriminator field
        filters: dict[
            str,
            ModelStringFilter
            | ModelNumericFilter
            | ModelDateTimeFilter
            | ModelListFilter
            | ModelMetadataFilter
            | ModelStatusFilter
            | ModelComplexFilter,
        ] = {}

        for name, filter_data in data.items():
            if isinstance(filter_data, dict) and "filter_type" in filter_data:
                filter_type = filter_data["filter_type"]

                if filter_type == "string":
                    filters[name] = ModelStringFilter.model_validate(filter_data)
                elif filter_type == "numeric":
                    filters[name] = ModelNumericFilter.model_validate(filter_data)
                elif filter_type == "datetime":
                    filters[name] = ModelDateTimeFilter.model_validate(filter_data)
                elif filter_type == "list" or filter_type == "list[Any]":
                    filters[name] = ModelListFilter.model_validate(filter_data)
                elif filter_type == "metadata":
                    filters[name] = ModelMetadataFilter.model_validate(filter_data)
                elif filter_type == "status":
                    filters[name] = ModelStatusFilter.model_validate(filter_data)
                elif filter_type == "complex":
                    filters[name] = ModelComplexFilter.model_validate(filter_data)
                else:
                    raise ModelOnexError(
                        message=f"Unknown filter_type '{filter_type}' for filter '{name}'",
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    )
            else:
                raise ModelOnexError(
                    message=f"Filter '{name}' must be a dict with 'filter_type' key",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )

        return cls(filters=filters)
