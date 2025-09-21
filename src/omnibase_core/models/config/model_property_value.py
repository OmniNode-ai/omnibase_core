"""
Property value model.

Type-safe property value container that replaces broad Union types
with structured validation and proper type handling.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from ...enums.enum_data_type import EnumDataType


class ModelPropertyValue(BaseModel):
    """
    Type-safe property value container.

    Replaces Union[str, int, float, bool, list[str], datetime] with
    structured value storage that maintains type information.
    """

    # Value storage with type tracking
    value: Any = Field(
        description="The actual property value",
    )

    value_type: EnumDataType = Field(
        description="Type of the stored value",
    )

    # Metadata
    is_validated: bool = Field(
        default=False,
        description="Whether value has been validated",
    )

    source: str | None = Field(
        None,
        description="Source of the property value",
    )

    @field_validator("value")
    @classmethod
    def validate_value_type(cls, v: Any, info: Any) -> Any:
        """Validate that value matches its declared type."""
        if hasattr(info, "data") and "value_type" in info.data:
            value_type = info.data["value_type"]

            # Type validation based on declared type
            if value_type == EnumDataType.STRING and not isinstance(v, str):
                raise ValueError(f"Value must be string, got {type(v)}")
            elif value_type == EnumDataType.INTEGER and not isinstance(v, int):
                raise ValueError(f"Value must be integer, got {type(v)}")
            elif value_type == EnumDataType.FLOAT and not isinstance(v, (int, float)):
                raise ValueError(f"Value must be float, got {type(v)}")
            elif value_type == EnumDataType.BOOLEAN and not isinstance(v, bool):
                raise ValueError(f"Value must be boolean, got {type(v)}")
            elif value_type == EnumDataType.LIST and not isinstance(v, list):
                raise ValueError(f"Value must be list, got {type(v)}")
            elif value_type == EnumDataType.DATETIME and not isinstance(v, datetime):
                raise ValueError(f"Value must be datetime, got {type(v)}")

        return v

    @classmethod
    def from_string(cls, value: str, source: str | None = None) -> ModelPropertyValue:
        """Create property value from string."""
        return cls(
            value=value,
            value_type=EnumDataType.STRING,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_int(cls, value: int, source: str | None = None) -> ModelPropertyValue:
        """Create property value from integer."""
        return cls(
            value=value,
            value_type=EnumDataType.INTEGER,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_float(cls, value: float, source: str | None = None) -> ModelPropertyValue:
        """Create property value from float."""
        return cls(
            value=value,
            value_type=EnumDataType.FLOAT,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_bool(cls, value: bool, source: str | None = None) -> ModelPropertyValue:
        """Create property value from boolean."""
        return cls(
            value=value,
            value_type=EnumDataType.BOOLEAN,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_list(
        cls, value: list[str], source: str | None = None
    ) -> ModelPropertyValue:
        """Create property value from string list."""
        return cls(
            value=value,
            value_type=EnumDataType.LIST,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_datetime(
        cls, value: datetime, source: str | None = None
    ) -> ModelPropertyValue:
        """Create property value from datetime."""
        return cls(
            value=value,
            value_type=EnumDataType.DATETIME,
            source=source,
            is_validated=True,
        )

    def as_string(self) -> str:
        """Get value as string."""
        if self.value_type == EnumDataType.STRING:
            return self.value
        return str(self.value)

    def as_int(self) -> int:
        """Get value as integer."""
        if self.value_type == EnumDataType.INTEGER:
            return self.value
        if isinstance(self.value, (int, float)):
            return int(self.value)
        if isinstance(self.value, str):
            return int(self.value)
        raise ValueError(f"Cannot convert {self.value_type} to int")

    def as_float(self) -> float:
        """Get value as float."""
        if self.value_type in (EnumDataType.FLOAT, EnumDataType.INTEGER):
            return float(self.value)
        if isinstance(self.value, str):
            return float(self.value)
        raise ValueError(f"Cannot convert {self.value_type} to float")

    def as_bool(self) -> bool:
        """Get value as boolean."""
        if self.value_type == EnumDataType.BOOLEAN:
            return self.value
        if isinstance(self.value, str):
            return self.value.lower() in ("true", "1", "yes", "on")
        return bool(self.value)


# Export the model
__all__ = ["ModelPropertyValue"]
