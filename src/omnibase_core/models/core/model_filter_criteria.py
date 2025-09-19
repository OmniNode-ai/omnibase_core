"""
Filter criteria model to replace Dict[str, Any] usage for filter fields.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

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
    logic: str = Field("AND", description="Logical operator (AND/OR)")

    # Time-based filters
    time_range: dict[str, datetime] | None = Field(
        None,
        description="Time range filter with 'start' and 'end'",
    )

    # Field selection
    include_fields: list[str] | None = Field(
        None,
        description="Fields to include in results",
    )
    exclude_fields: list[str] | None = Field(
        None,
        description="Fields to exclude from results",
    )

    # Sorting
    sort_by: str | None = Field(None, description="Field to sort by")
    sort_order: str = Field("asc", description="Sort order (asc/desc)")

    # Pagination
    limit: int | None = Field(None, description="Maximum results to return")
    offset: int | None = Field(None, description="Results offset for pagination")

    # Advanced filters
    tags: list[str] | None = Field(None, description="Tag filters")
    categories: list[str] | None = Field(None, description="Category filters")
    severity_levels: list[str] | None = Field(
        None,
        description="Severity level filters",
    )

    # Custom filters (for extensibility)
    custom_filters: ModelCustomFilters = Field(
        default_factory=ModelCustomFilters,
        description="Custom filter extensions",
    )

    model_config = ConfigDict()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for current standards."""
        # Use model_dump() as base and transform custom filters
        data = self.model_dump(exclude_none=True)
        # Convert custom filters to dict if present
        if self.custom_filters and self.custom_filters.filters:
            data["custom_filters"] = self.custom_filters.to_dict()
        return data

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> Optional["ModelFilterCriteria"]:
        """Create from dictionary for easy migration."""
        if data is None:
            return None

        # Handle legacy format conversion
        if "conditions" not in data and data:
            # Convert simple key-value filters to conditions
            conditions = []
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
                    conditions.append(
                        ModelFilterCondition(
                            field=key,
                            operator=ModelFilterOperator(
                                operator="eq", value=value, case_sensitive=True
                            ),
                            negate=False,
                        ),
                    )
            data["conditions"] = conditions

        # Convert custom_filters if present
        if "custom_filters" in data and isinstance(data["custom_filters"], dict):
            data["custom_filters"] = ModelCustomFilters.from_dict(
                data["custom_filters"],
            )

        return cls(**data)

    def add_condition(self, field: str, operator: str, value: Any) -> None:
        """Add a filter condition."""
        self.conditions.append(
            ModelFilterCondition(
                field=field,
                operator=ModelFilterOperator(
                    operator=operator, value=value, case_sensitive=True
                ),
                negate=False,
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
