"""Collection of custom filters model."""

from typing import Any, Union

from pydantic import BaseModel, Field

from .model_complex_filter import ModelComplexFilter
from .model_custom_filter_base import ModelCustomFilterBase
from .model_datetime_filter import ModelDateTimeFilter
from .model_list_filter import ModelListFilter
from .model_metadata_filter import ModelMetadataFilter
from .model_numeric_filter import ModelNumericFilter
from .model_status_filter import ModelStatusFilter
from .model_string_filter import ModelStringFilter

# Type alias for the filter union
FilterType = Union[
    ModelStringFilter,
    ModelNumericFilter,
    ModelDateTimeFilter,
    ModelListFilter,
    ModelMetadataFilter,
    ModelStatusFilter,
    ModelComplexFilter,
]


class ModelCustomFilters(BaseModel):
    """
    Collection of custom filters.

    Replaces Dict[str, Any] for custom_filters fields with typed filters.
    """

    filters: dict[str, FilterType] = Field(
        default_factory=dict, description="Named custom filters"
    )

    def add_string_filter(self, name: str, pattern: str, **kwargs: Any) -> None:
        """Add a string filter."""
        self.filters[name] = ModelStringFilter(pattern=pattern, **kwargs)

    def add_numeric_filter(self, name: str, **kwargs: Any) -> None:
        """Add a numeric filter."""
        self.filters[name] = ModelNumericFilter(**kwargs)

    def add_datetime_filter(self, name: str, **kwargs: Any) -> None:
        """Add a datetime filter."""
        self.filters[name] = ModelDateTimeFilter(**kwargs)

    def add_list_filter(self, name: str, values: list[Any], **kwargs: Any) -> None:
        """Add a list filter."""
        self.filters[name] = ModelListFilter(values=values, **kwargs)

    def add_metadata_filter(
        self, name: str, key: str, value: Any, **kwargs: Any
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

    def get_filter(self, name: str) -> FilterType | None:
        """Get a filter by name."""
        return self.filters.get(name)

    def remove_filter(self, name: str) -> None:
        """Remove a filter by name."""
        self.filters.pop(name, None)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (for current standards)."""
        # Custom transformation logic for filters dictionary
        return {name: filter_obj.to_dict() for name, filter_obj in self.filters.items()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelCustomFilters":
        """Create from dictionary (for migration)."""
        filters: dict[str, FilterType] = {}

        for name, filter_data in data.items():
            if isinstance(filter_data, dict) and "filter_type" in filter_data:
                filter_type = filter_data["filter_type"]

                if filter_type == "string":
                    filters[name] = ModelStringFilter(**filter_data)
                elif filter_type == "numeric":
                    filters[name] = ModelNumericFilter(**filter_data)
                elif filter_type == "datetime":
                    filters[name] = ModelDateTimeFilter(**filter_data)
                elif filter_type == "list" or filter_type == "list[Any]":
                    filters[name] = ModelListFilter(**filter_data)
                elif filter_type == "metadata":
                    filters[name] = ModelMetadataFilter(**filter_data)
                elif filter_type == "status":
                    filters[name] = ModelStatusFilter(**filter_data)
                elif filter_type == "complex":
                    filters[name] = ModelComplexFilter(**filter_data)
                else:
                    # For unknown types, create a generic filter
                    # This maintains compatibility
                    filters[name] = ModelStringFilter(
                        pattern=str(filter_data),
                        filter_type="legacy",
                    )
            else:
                # Legacy format - convert to string filter
                filters[name] = ModelStringFilter(
                    pattern=str(filter_data),
                    filter_type="legacy",
                )

        return cls(filters=filters)
