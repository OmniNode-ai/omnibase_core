"""
Collection of custom filters model.

Strongly typed collection replacing Dict[str, Any] for custom_filters fields.
"""

from datetime import datetime
from typing import Any, Union

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_filter_type import EnumFilterType

from .model_complex_filter import ModelComplexFilter
from .model_datetime_filter import ModelDateTimeFilter
from .model_list_filter import ModelListFilter
from .model_metadata_filter import ModelMetadataFilter
from .model_numeric_filter import ModelNumericFilter
from .model_status_filter import ModelStatusFilter
from .model_string_filter import ModelStringFilter

# Type alias for filter union
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

    Strongly typed collection replacing Dict[str, Any] for custom_filters fields
    with no magic strings or poorly typed dictionaries.
    """

    filters: dict[str, FilterType] = Field(
        default_factory=dict,
        description="Named custom filters with strong typing",
    )

    def add_string_filter(
        self,
        name: str,
        pattern: str,
        enabled: bool = True,
        priority: int = 0,
        case_sensitive: bool = True,
        regex: bool = False,
        contains: bool = True,
    ) -> None:
        """Add a string filter with full type safety."""
        self.filters[name] = ModelStringFilter(
            pattern=pattern,
            enabled=enabled,
            priority=priority,
            case_sensitive=case_sensitive,
            regex=regex,
            contains=contains,
            filter_type=EnumFilterType.STRING,
        )

    def add_numeric_filter(
        self,
        name: str,
        min_value: float | None = None,
        max_value: float | None = None,
        exact_value: float | None = None,
        tolerance: float = 0.0,
        enabled: bool = True,
        priority: int = 0,
    ) -> None:
        """Add a numeric filter with full type safety."""
        self.filters[name] = ModelNumericFilter(
            min_value=min_value,
            max_value=max_value,
            exact_value=exact_value,
            tolerance=tolerance,
            enabled=enabled,
            priority=priority,
            filter_type=EnumFilterType.NUMERIC,
        )

    def add_datetime_filter(
        self,
        name: str,
        after: datetime | None = None,
        before: datetime | None = None,
        on_date: datetime | None = None,
        relative_days: int | None = None,
        enabled: bool = True,
        priority: int = 0,
    ) -> None:
        """Add a datetime filter with full type safety."""
        self.filters[name] = ModelDateTimeFilter(
            after=after,
            before=before,
            on_date=on_date,
            relative_days=relative_days,
            enabled=enabled,
            priority=priority,
            filter_type=EnumFilterType.DATETIME,
        )

    def add_list_filter(
        self,
        name: str,
        values: list[str],
        match_all: bool = False,
        exclude: bool = False,
        enabled: bool = True,
        priority: int = 0,
    ) -> None:
        """Add a list filter with full type safety."""
        self.filters[name] = ModelListFilter(
            values=values,
            match_all=match_all,
            exclude=exclude,
            enabled=enabled,
            priority=priority,
            filter_type=EnumFilterType.LIST,
        )

    def add_metadata_filter(
        self,
        name: str,
        metadata_key: str,
        metadata_value: str,
        enabled: bool = True,
        priority: int = 0,
    ) -> None:
        """Add a metadata filter with full type safety."""
        self.filters[name] = ModelMetadataFilter(
            metadata_key=metadata_key,
            metadata_value=metadata_value,
            enabled=enabled,
            priority=priority,
            filter_type=EnumFilterType.METADATA,
        )

    def add_status_filter(
        self,
        name: str,
        allowed_statuses: list[str],
        blocked_statuses: list[str] | None = None,
        include_unknown: bool = False,
        enabled: bool = True,
        priority: int = 0,
    ) -> None:
        """Add a status filter with full type safety."""
        self.filters[name] = ModelStatusFilter(
            allowed_statuses=allowed_statuses,
            blocked_statuses=blocked_statuses or [],
            include_unknown=include_unknown,
            enabled=enabled,
            priority=priority,
            filter_type=EnumFilterType.STATUS,
        )

    def get_filter(self, name: str) -> FilterType | None:
        """Get a filter by name with strong typing."""
        return self.filters.get(name)

    def remove_filter(self, name: str) -> bool:
        """Remove a filter by name, return True if removed."""
        if name in self.filters:
            del self.filters[name]
            return True
        return False

    def get_filter_names(self) -> list[str]:
        """Get all filter names."""
        return list(self.filters.keys())

    def get_enabled_filters(self) -> dict[str, FilterType]:
        """Get only enabled filters."""
        return {
            name: filter_obj
            for name, filter_obj in self.filters.items()
            if hasattr(filter_obj, "enabled") and filter_obj.enabled
        }

    def filter_count(self) -> int:
        """Get total number of filters."""
        return len(self.filters)

    def enabled_filter_count(self) -> int:
        """Get number of enabled filters."""
        return len(self.get_enabled_filters())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with strong typing preserved."""
        return {
            name: filter_obj.model_dump() for name, filter_obj in self.filters.items()
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelCustomFilters":
        """Create from dictionary with strict type validation."""
        filters: dict[str, FilterType] = {}

        for name, filter_data in data.items():
            if not isinstance(filter_data, dict):
                msg = f"Filter {name} must be a dictionary, got {type(filter_data)}"
                raise ValueError(
                    msg,
                )

            filter_type_value = filter_data.get("filter_type")
            if not filter_type_value:
                msg = f"Filter {name} missing required field 'filter_type'"
                raise ValueError(msg)

            try:
                filter_type = EnumFilterType(filter_type_value)
            except ValueError:
                msg = f"Filter {name} has invalid filter_type: {filter_type_value}"
                raise ValueError(
                    msg,
                )

            # Create the appropriate filter type with validation
            if filter_type == EnumFilterType.STRING:
                filters[name] = ModelStringFilter(**filter_data)
            elif filter_type == EnumFilterType.NUMERIC:
                filters[name] = ModelNumericFilter(**filter_data)
            elif filter_type == EnumFilterType.DATETIME:
                filters[name] = ModelDateTimeFilter(**filter_data)
            elif filter_type == EnumFilterType.LIST:
                filters[name] = ModelListFilter(**filter_data)
            elif filter_type == EnumFilterType.METADATA:
                filters[name] = ModelMetadataFilter(**filter_data)
            elif filter_type == EnumFilterType.STATUS:
                filters[name] = ModelStatusFilter(**filter_data)
            elif filter_type == EnumFilterType.COMPLEX:
                filters[name] = ModelComplexFilter(**filter_data)

        return cls(filters=filters)

    @classmethod
    def create_empty(cls) -> "ModelCustomFilters":
        """Create an empty filter collection."""
        return cls()


# Export for use
__all__ = ["FilterType", "ModelCustomFilters"]
