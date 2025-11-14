from typing import Any

from pydantic import Field

"""
ModelMaskData: Structured data model for masking operations.

This model provides strongly typed data masking without using Any types.
"""

from pydantic import BaseModel


class ModelMaskData(BaseModel):
    """Structured data model for masking operations."""

    string_data: dict[str, str] = Field(
        default_factory=dict,
        description="String data fields",
    )
    integer_data: dict[str, int] = Field(
        default_factory=dict,
        description="Integer data fields",
    )
    boolean_data: dict[str, bool] = Field(
        default_factory=dict,
        description="Boolean data fields",
    )
    list_data: dict[str, list[str]] = Field(
        default_factory=dict,
        description="List data fields",
    )
    nested_data: dict[str, "ModelMaskData"] = Field(
        default_factory=dict,
        description="Nested data structures",
    )

    def to_dict(self) -> dict[str, str | int | bool | list[str] | dict[str, Any]]:
        """Convert to a dictionary representation."""
        # Custom flattening logic with recursive nested data handling
        result: dict[str, str | int | bool | list[str] | dict[str, Any]] = {}
        result.update(self.string_data)
        result.update(self.integer_data)
        result.update(self.boolean_data)
        result.update(self.list_data)
        for key, nested in self.nested_data.items():
            result[key] = nested.to_dict()
        return result

    @classmethod
    def from_dict(
        cls,
        data: dict[str, str | int | bool | list[str] | dict[str, Any]],
    ) -> "ModelMaskData":
        """Create from a dictionary."""
        string_data: dict[str, str] = {}
        integer_data: dict[str, int] = {}
        boolean_data: dict[str, bool] = {}
        list_data: dict[str, list[str]] = {}
        nested_data: dict[str, ModelMaskData] = {}

        for key, value in data.items():
            if isinstance(value, str):
                string_data[key] = value
            elif isinstance(value, bool):
                boolean_data[key] = value
            elif isinstance(value, int):
                integer_data[key] = value
            elif isinstance(value, list) and all(
                isinstance(item, str) for item in value
            ):
                list_data[key] = value
            elif isinstance(value, dict):
                nested_data[key] = cls.from_dict(value)

        return cls(
            string_data=string_data,
            integer_data=integer_data,
            boolean_data=boolean_data,
            list_data=list_data,
            nested_data=nested_data,
        )
