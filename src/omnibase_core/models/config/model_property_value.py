"""
Property value model.

Type-safe property value container that replaces broad Union types
with structured validation and proper type handling.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from ...enums.enum_core_error_code import EnumCoreErrorCode
from ...enums.enum_property_type import EnumPropertyType
from ...exceptions.onex_error import OnexError
from ...models.common.model_error_context import ModelErrorContext
from ...models.common.model_schema_value import ModelSchemaValue


class ModelPropertyValue(BaseModel):
    """
    Type-safe property value container.

    Uses discriminated union pattern with runtime validation to ensure
    type safety while avoiding overly broad Union types.
    """

    # Value storage with runtime validation - Any type with discriminated validation
    value: Any = Field(
        description="The actual property value - validated against value_type",
    )

    value_type: EnumPropertyType = Field(
        description="Type discriminator for the stored value",
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
    def validate_value_type(cls, v: Any, info: ValidationInfo) -> Any:
        """Validate that value matches its declared type."""
        if hasattr(info, "data") and "value_type" in info.data:
            value_type = info.data["value_type"]

            # Type validation based on declared type
            if value_type == EnumPropertyType.STRING and not isinstance(v, str):
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Value must be string, got {type(v)}",
                    details=ModelErrorContext.with_context(
                        {
                            "expected_type": ModelSchemaValue.from_value("string"),
                            "actual_type": ModelSchemaValue.from_value(str(type(v))),
                            "value": ModelSchemaValue.from_value(str(v)),
                        },
                    ),
                )
            if value_type == EnumPropertyType.INTEGER and not isinstance(v, int):
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Value must be integer, got {type(v)}",
                    details=ModelErrorContext.with_context(
                        {
                            "expected_type": ModelSchemaValue.from_value("integer"),
                            "actual_type": ModelSchemaValue.from_value(str(type(v))),
                            "value": ModelSchemaValue.from_value(str(v)),
                        },
                    ),
                )
            if value_type == EnumPropertyType.FLOAT and not isinstance(
                v,
                (int, float),
            ):
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Value must be float, got {type(v)}",
                    details=ModelErrorContext.with_context(
                        {
                            "expected_type": ModelSchemaValue.from_value("float"),
                            "actual_type": ModelSchemaValue.from_value(str(type(v))),
                            "value": ModelSchemaValue.from_value(str(v)),
                        },
                    ),
                )
            if value_type == EnumPropertyType.BOOLEAN and not isinstance(v, bool):
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Value must be boolean, got {type(v)}",
                    details=ModelErrorContext.with_context(
                        {
                            "expected_type": ModelSchemaValue.from_value("boolean"),
                            "actual_type": ModelSchemaValue.from_value(str(type(v))),
                            "value": ModelSchemaValue.from_value(str(v)),
                        },
                    ),
                )
            if value_type in (
                EnumPropertyType.STRING_LIST,
                EnumPropertyType.INTEGER_LIST,
                EnumPropertyType.FLOAT_LIST,
            ) and not isinstance(v, list):
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Value must be list, got {type(v)}",
                    details=ModelErrorContext.with_context(
                        {
                            "expected_type": ModelSchemaValue.from_value("list"),
                            "actual_type": ModelSchemaValue.from_value(str(type(v))),
                            "value": ModelSchemaValue.from_value(str(v)),
                        },
                    ),
                )
            if value_type == EnumPropertyType.DATETIME and not isinstance(
                v,
                datetime,
            ):
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Value must be datetime, got {type(v)}",
                    details=ModelErrorContext.with_context(
                        {
                            "expected_type": ModelSchemaValue.from_value("datetime"),
                            "actual_type": ModelSchemaValue.from_value(str(type(v))),
                            "value": ModelSchemaValue.from_value(str(v)),
                        },
                    ),
                )
            if value_type == EnumPropertyType.UUID and not isinstance(v, (UUID, str)):
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Value must be UUID or string, got {type(v)}",
                    details=ModelErrorContext.with_context(
                        {
                            "expected_type": ModelSchemaValue.from_value("uuid"),
                            "actual_type": ModelSchemaValue.from_value(str(type(v))),
                            "value": ModelSchemaValue.from_value(str(v)),
                        },
                    ),
                )

        return v

    @classmethod
    def from_string(cls, value: str, source: str | None = None) -> ModelPropertyValue:
        """Create property value from string."""
        return cls(
            value=value,
            value_type=EnumPropertyType.STRING,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_int(cls, value: int, source: str | None = None) -> ModelPropertyValue:
        """Create property value from integer."""
        return cls(
            value=value,
            value_type=EnumPropertyType.INTEGER,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_float(cls, value: float, source: str | None = None) -> ModelPropertyValue:
        """Create property value from float."""
        return cls(
            value=value,
            value_type=EnumPropertyType.FLOAT,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_bool(cls, value: bool, source: str | None = None) -> ModelPropertyValue:
        """Create property value from boolean."""
        return cls(
            value=value,
            value_type=EnumPropertyType.BOOLEAN,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_string_list(
        cls,
        value: list[str],
        source: str | None = None,
    ) -> ModelPropertyValue:
        """Create property value from string list."""
        return cls(
            value=value,
            value_type=EnumPropertyType.STRING_LIST,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_int_list(
        cls,
        value: list[int],
        source: str | None = None,
    ) -> ModelPropertyValue:
        """Create property value from integer list."""
        return cls(
            value=value,
            value_type=EnumPropertyType.INTEGER_LIST,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_float_list(
        cls,
        value: list[float],
        source: str | None = None,
    ) -> ModelPropertyValue:
        """Create property value from float list."""
        return cls(
            value=value,
            value_type=EnumPropertyType.FLOAT_LIST,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_datetime(
        cls,
        value: datetime,
        source: str | None = None,
    ) -> ModelPropertyValue:
        """Create property value from datetime."""
        return cls(
            value=value,
            value_type=EnumPropertyType.DATETIME,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_uuid(
        cls,
        value: UUID | str,
        source: str | None = None,
    ) -> ModelPropertyValue:
        """Create property value from UUID."""
        return cls(
            value=value,
            value_type=EnumPropertyType.UUID,
            source=source,
            is_validated=True,
        )

    @classmethod
    def from_list(
        cls,
        value: list[str],
        source: str | None = None,
    ) -> ModelPropertyValue:
        """Create property value from string list (backward compatibility alias)."""
        return cls.from_string_list(value, source)

    def as_string(self) -> str:
        """Get value as string."""
        if self.value_type == EnumPropertyType.STRING:
            return str(self.value)
        return str(self.value)

    def as_int(self) -> int:
        """Get value as integer."""
        if self.value_type == EnumPropertyType.INTEGER:
            return int(self.value)
        if isinstance(self.value, (int, float)):
            return int(self.value)
        if isinstance(self.value, str):
            return int(self.value)
        raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Cannot convert {self.value_type} to int",
            details=ModelErrorContext.with_context(
                {
                    "source_type": ModelSchemaValue.from_value(str(self.value_type)),
                    "target_type": ModelSchemaValue.from_value("int"),
                    "value": ModelSchemaValue.from_value(str(self.value)),
                },
            ),
        )

    def as_float(self) -> float:
        """Get value as float."""
        if self.value_type in (EnumPropertyType.FLOAT, EnumPropertyType.INTEGER):
            return float(self.value)
        if isinstance(self.value, str):
            return float(self.value)
        raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Cannot convert {self.value_type} to float",
            details=ModelErrorContext.with_context(
                {
                    "source_type": ModelSchemaValue.from_value(str(self.value_type)),
                    "target_type": ModelSchemaValue.from_value("float"),
                    "value": ModelSchemaValue.from_value(str(self.value)),
                },
            ),
        )

    def as_bool(self) -> bool:
        """Get value as boolean."""
        if self.value_type == EnumPropertyType.BOOLEAN:
            return bool(self.value)
        if isinstance(self.value, str):
            return self.value.lower() in ("true", "1", "yes", "on")
        return bool(self.value)

    def as_list(self) -> list[Any]:
        """Get value as list."""
        if self.value_type in (
            EnumPropertyType.STRING_LIST,
            EnumPropertyType.INTEGER_LIST,
            EnumPropertyType.FLOAT_LIST,
        ):
            return list(self.value)
        raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Cannot convert {self.value_type} to list",
            details=ModelErrorContext.with_context(
                {
                    "source_type": ModelSchemaValue.from_value(str(self.value_type)),
                    "target_type": ModelSchemaValue.from_value("list"),
                    "value": ModelSchemaValue.from_value(str(self.value)),
                },
            ),
        )

    def as_uuid(self) -> UUID:
        """Get value as UUID."""
        if self.value_type == EnumPropertyType.UUID:
            if isinstance(self.value, UUID):
                return self.value
            return UUID(self.value)
        raise OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Cannot convert {self.value_type} to UUID",
            details=ModelErrorContext.with_context(
                {
                    "source_type": ModelSchemaValue.from_value(str(self.value_type)),
                    "target_type": ModelSchemaValue.from_value("UUID"),
                    "value": ModelSchemaValue.from_value(str(self.value)),
                },
            ),
        )


# Export the model
__all__ = ["ModelPropertyValue"]
