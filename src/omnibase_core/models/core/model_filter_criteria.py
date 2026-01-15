"""
Filter criteria model to replace Dict[str, Any] usage for filter fields.
"""

from __future__ import annotations

import logging
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

from omnibase_core.types.type_serializable_value import SerializedDict

from .model_custom_filter import ModelCustomFilters
from .model_filter_condition import ModelFilterCondition
from .model_filter_operator import ModelFilterOperator

# Compatibility aliases
FilterOperator = ModelFilterOperator
FilterCondition = ModelFilterCondition


class ModelFilterCriteria(BaseModel):
    """
    Filter criteria with typed fields.
    Replaces Dict[str, Any] for filter_criteria fields.
    """

    # Basic filters
    conditions: list[ModelFilterCondition] = Field(
        default_factory=list,
        description="Filter conditions",
    )

    # Logical operators
    logic: str = Field(default="AND", description="Logical operator (AND/OR)")

    # Time-based filters
    time_range: dict[str, datetime] | None = Field(
        default=None,
        description="Time range filter with 'start' and 'end'",
    )

    # Field selection
    include_fields: list[str] | None = Field(
        default=None,
        description="Fields to include in results",
    )
    exclude_fields: list[str] | None = Field(
        default=None,
        description="Fields to exclude from results",
    )

    # Sorting
    sort_by: str | None = Field(default=None, description="Field to sort by")
    sort_order: str = Field(default="asc", description="Sort order (asc/desc)")

    # Pagination
    limit: int | None = Field(default=None, description="Maximum results to return")
    offset: int | None = Field(
        default=None, description="Results offset for pagination"
    )

    # Advanced filters
    tags: list[str] | None = Field(default=None, description="Tag filters")
    categories: list[str] | None = Field(default=None, description="Category filters")
    severity_levels: list[str] | None = Field(
        default=None,
        description="Severity level filters",
    )

    # Custom filters (for extensibility)
    custom_filters: ModelCustomFilters = Field(
        default_factory=ModelCustomFilters,
        description="Custom filter extensions",
    )

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    def to_dict(self) -> SerializedDict:
        """Convert to dictionary for current standards."""
        # Use model_dump() as base and transform custom filters
        data = self.model_dump(exclude_none=True)
        # Convert custom filters to SerializedDict if present
        if self.custom_filters and self.custom_filters.filters:
            data["custom_filters"] = self.custom_filters.to_dict()
        return data

    @classmethod
    def from_dict(
        cls,
        data: SerializedDict | None,
    ) -> ModelFilterCriteria | None:
        """Create from dictionary for easy migration."""
        if data is None:
            return None

        # Use mutable dict for type-safe modifications
        mutable_data: dict[str, object] = dict(data)

        # Handle legacy format conversion
        if "conditions" not in mutable_data and mutable_data:
            # Convert simple key-value filters to conditions
            conditions: list[ModelFilterCondition] = []
            for key, value in data.items():
                if key not in [
                    "logic",
                    "time_range",
                    "include_fields",
                    "exclude_fields",
                    "sort_by",
                    "sort_order",
                    "limit",
                    "offset",
                ]:
                    # Coerce value to acceptable type for ModelFilterOperator
                    if isinstance(value, (str, int, float, bool)):
                        coerced_value: (
                            str | int | float | bool | list[str | int | float | bool]
                        ) = value
                    elif isinstance(value, list):
                        # Filter list items to acceptable types
                        coerced_value = [
                            v for v in value if isinstance(v, (str, int, float, bool))
                        ]
                    else:
                        # fallback-ok: skip unsupported types during legacy migration
                        logger.debug(
                            "Skipping filter field '%s' with unsupported type %s",
                            key,
                            type(value).__name__,
                        )
                        continue
                    conditions.append(
                        ModelFilterCondition(
                            field=key,
                            operator=ModelFilterOperator(
                                operator="eq", value=coerced_value
                            ),
                        ),
                    )
            mutable_data["conditions"] = conditions

        # Convert custom_filters if present
        custom_filters_raw = mutable_data.get("custom_filters")
        if custom_filters_raw is not None and isinstance(custom_filters_raw, dict):
            mutable_data["custom_filters"] = ModelCustomFilters.from_dict(
                custom_filters_raw,
            )

        return cls.model_validate(mutable_data)

    def add_condition(
        self,
        field: str,
        operator: str,
        value: str | int | float | bool | list[str | int | float | bool],
    ) -> None:
        """Add a filter condition."""
        self.conditions.append(
            ModelFilterCondition(
                field=field,
                operator=ModelFilterOperator(operator=operator, value=value),
            ),
        )

    def to_query_string(self) -> str:
        """Convert to query string format."""
        parts = []
        for condition in self.conditions:
            op = condition.operator.operator
            val = condition.operator.value
            parts.append(f"{condition.field}__{op}={val}")

        if self.sort_by:
            parts.append(f"sort={self.sort_by}:{self.sort_order}")

        if self.limit:
            parts.append(f"limit={self.limit}")

        if self.offset:
            parts.append(f"offset={self.offset}")

        return "&".join(parts)


# Compatibility alias
FilterCriteria = ModelFilterCriteria
