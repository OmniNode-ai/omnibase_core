from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelYamlList(BaseModel):
    """Model for YAML files that are primarily lists.

    Uses ModelSchemaValue for type-safe list values.
    """

    model_config = ConfigDict(extra="allow")

    # For files that are root-level arrays
    root_list: list[ModelSchemaValue] = Field(
        default_factory=list, description="Root level list (type-safe)"
    )

    @field_validator("root_list", mode="before")
    @classmethod
    def convert_root_list_to_schema(
        cls, v: list[Any] | list[ModelSchemaValue] | None
    ) -> list[ModelSchemaValue]:
        """Convert values to ModelSchemaValue for type safety."""
        if not v:
            return []
        # If already ModelSchemaValue instances, return as-is
        if len(v) > 0 and isinstance(v[0], ModelSchemaValue):
            return v  # type: ignore[return-value]
        # Convert raw values to ModelSchemaValue
        return [ModelSchemaValue.from_value(item) for item in v]

    def __init__(
        self, data: list[Any] | list[ModelSchemaValue] | None = None, **kwargs: Any
    ) -> None:
        """Handle case where YAML root is a list."""
        if data is not None and isinstance(data, list):
            # Filter out root_list from kwargs to avoid conflict
            filtered_kwargs = {k: v for k, v in kwargs.items() if k != "root_list"}
            super().__init__(root_list=data, **filtered_kwargs)
            return
        # data is None or not a list - use default initialization
        super().__init__(**kwargs)
