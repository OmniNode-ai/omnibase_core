#!/usr/bin/env python3
"""
ONEX Generic Value Model

This module provides a strongly typed generic value model that can represent
different data types in a type-safe manner for validation and testing.
"""

import json

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_value_type import EnumValueType
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelGenericValue(BaseModel):
    """
    Generic value model that can represent different data types in a type-safe manner.

    This model stores a value along with its type information, ensuring type safety
    while allowing flexible value storage for validation and testing scenarios.
    """

    value_type: EnumValueType = Field(description="Type of the stored value")
    string_value: str | None = Field(default=None, description="String value")
    integer_value: int | None = Field(default=None, description="Integer value")
    float_value: float | None = Field(default=None, description="Float value")
    boolean_value: bool | None = Field(default=None, description="Boolean value")
    list_string_value: list[str] | None = Field(
        default=None,
        description="List of strings",
    )
    list_integer_value: list[int] | None = Field(
        default=None,
        description="List of integers",
    )
    dict_value: str | None = Field(
        default=None,
        description="Dictionary value stored as JSON string",
    )

    @field_validator("string_value")
    @classmethod
    def validate_string_value(cls, v: str | None, info: ValidationInfo) -> str | None:
        """Validate string value is set when type is STRING"""
        data = info.data if info else {}
        if data.get("value_type") == EnumValueType.STRING and v is None:
            msg = "string_value must be set when value_type is STRING"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        if data.get("value_type") != EnumValueType.STRING and v is not None:
            msg = "string_value should only be set when value_type is STRING"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("integer_value")
    @classmethod
    def validate_integer_value(cls, v: int | None, info: ValidationInfo) -> int | None:
        """Validate integer value is set when type is INTEGER"""
        data = info.data if info else {}
        if data.get("value_type") == EnumValueType.INTEGER and v is None:
            msg = "integer_value must be set when value_type is INTEGER"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        if data.get("value_type") != EnumValueType.INTEGER and v is not None:
            msg = "integer_value should only be set when value_type is INTEGER"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("float_value")
    @classmethod
    def validate_float_value(
        cls, v: float | None, info: ValidationInfo
    ) -> float | None:
        """Validate float value is set when type is FLOAT"""
        data = info.data if info else {}
        if data.get("value_type") == EnumValueType.FLOAT and v is None:
            msg = "float_value must be set when value_type is FLOAT"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        if data.get("value_type") != EnumValueType.FLOAT and v is not None:
            msg = "float_value should only be set when value_type is FLOAT"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("boolean_value")
    @classmethod
    def validate_boolean_value(
        cls, v: bool | None, info: ValidationInfo
    ) -> bool | None:
        """Validate boolean value is set when type is BOOLEAN"""
        data = info.data if info else {}
        if data.get("value_type") == EnumValueType.BOOLEAN and v is None:
            msg = "boolean_value must be set when value_type is BOOLEAN"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        if data.get("value_type") != EnumValueType.BOOLEAN and v is not None:
            msg = "boolean_value should only be set when value_type is BOOLEAN"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("list_string_value")
    @classmethod
    def validate_list_string_value(
        cls, v: list[str] | None, info: ValidationInfo
    ) -> list[str] | None:
        """Validate list_string_value is set when value_type is LIST_STRING.

        Args:
            v: The list[str] | None value to validate.
            info: Pydantic validation info containing other field values.

        Returns:
            The validated value unchanged.

        Raises:
            ModelOnexError: If list_string_value is None when value_type is LIST_STRING,
                or if list_string_value is set when value_type is not LIST_STRING.
        """
        data = info.data if info else {}
        if data.get("value_type") == EnumValueType.LIST_STRING and v is None:
            msg = "list_string_value must be set when value_type is LIST_STRING"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        if data.get("value_type") != EnumValueType.LIST_STRING and v is not None:
            msg = "list_string_value should only be set when value_type is LIST_STRING"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("list_integer_value")
    @classmethod
    def validate_list_integer_value(
        cls, v: list[int] | None, info: ValidationInfo
    ) -> list[int] | None:
        """Validate list_integer_value is set when value_type is LIST_INTEGER.

        Args:
            v: The list[int] | None value to validate.
            info: Pydantic validation info containing other field values.

        Returns:
            The validated value unchanged.

        Raises:
            ModelOnexError: If list_integer_value is None when value_type is LIST_INTEGER,
                or if list_integer_value is set when value_type is not LIST_INTEGER.
        """
        data = info.data if info else {}
        if data.get("value_type") == EnumValueType.LIST_INTEGER and v is None:
            msg = "list_integer_value must be set when value_type is LIST_INTEGER"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        if data.get("value_type") != EnumValueType.LIST_INTEGER and v is not None:
            msg = (
                "list_integer_value should only be set when value_type is LIST_INTEGER"
            )
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("dict_value")
    @classmethod
    def validate_dict_value(cls, v: str | None, info: ValidationInfo) -> str | None:
        """Validate dict_value is set when value_type is DICT.

        Args:
            v: The str | None value to validate (dict stored as JSON string).
            info: Pydantic validation info containing other field values.

        Returns:
            The validated value unchanged.

        Raises:
            ModelOnexError: If dict_value is None when value_type is DICT,
                or if dict_value is set when value_type is not DICT.
        """
        data = info.data if info else {}
        if data.get("value_type") == EnumValueType.DICT and v is None:
            msg = "dict_value must be set when value_type is DICT"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        if data.get("value_type") != EnumValueType.DICT and v is not None:
            msg = "dict_value should only be set when value_type is DICT"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    def get_python_value(
        self,
    ) -> str | int | float | bool | list[str] | list[int] | dict[str, object] | None:
        """Get the actual Python value based on the value_type.

        Returns:
            The stored value as its native Python type:
            - str for STRING
            - int for INTEGER
            - float for FLOAT
            - bool for BOOLEAN
            - list[str] for LIST_STRING
            - list[int] for LIST_INTEGER
            - dict[str, object] for DICT (parsed from JSON)
            - None for NULL

        Raises:
            ModelOnexError: If value_type is not a recognized EnumValueType.
        """
        if self.value_type == EnumValueType.STRING:
            return self.string_value
        if self.value_type == EnumValueType.INTEGER:
            return self.integer_value
        if self.value_type == EnumValueType.FLOAT:
            return self.float_value
        if self.value_type == EnumValueType.BOOLEAN:
            return self.boolean_value
        if self.value_type == EnumValueType.LIST_STRING:
            return self.list_string_value
        if self.value_type == EnumValueType.LIST_INTEGER:
            return self.list_integer_value
        if self.value_type == EnumValueType.DICT:
            return json.loads(self.dict_value) if self.dict_value else {}
        if self.value_type == EnumValueType.NULL:
            return None
        msg = f"Unknown value type: {self.value_type}"  # type: ignore[unreachable]
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=msg,
        )

    @classmethod
    def from_python_value(
        cls,
        value: str
        | int
        | float
        | bool
        | list[str]
        | list[int]
        | dict[str, object]
        | None,
    ) -> "ModelGenericValue":
        """Create ModelGenericValue from a Python value.

        Args:
            value: A Python value to wrap. Supported types:
                - None -> NULL
                - str -> STRING
                - bool -> BOOLEAN (checked before int)
                - int -> INTEGER
                - float -> FLOAT
                - list[str] -> LIST_STRING
                - list[int] -> LIST_INTEGER
                - dict[str, object] -> DICT (serialized to JSON)

        Returns:
            A new ModelGenericValue instance with appropriate value_type.

        Raises:
            ModelOnexError: If the value type is not supported, or if a list
                contains mixed or unsupported element types.
        """
        if value is None:
            return cls(value_type=EnumValueType.NULL)
        if isinstance(value, str):
            return cls(value_type=EnumValueType.STRING, string_value=value)
        if isinstance(
            value, bool
        ):  # Must check bool before int (bool is subclass of int)
            return cls(value_type=EnumValueType.BOOLEAN, boolean_value=value)
        if isinstance(value, int):
            return cls(value_type=EnumValueType.INTEGER, integer_value=value)
        if isinstance(value, float):
            return cls(value_type=EnumValueType.FLOAT, float_value=value)
        if isinstance(value, list):
            if all(isinstance(item, str) for item in value):
                # Narrow type after all() check - mypy can't infer this
                str_list: list[str] = [str(item) for item in value]
                return cls(
                    value_type=EnumValueType.LIST_STRING,
                    list_string_value=str_list,
                )
            if all(isinstance(item, int) for item in value):
                # Narrow type after all() check - mypy can't infer this
                int_list: list[int] = [int(item) for item in value]
                return cls(
                    value_type=EnumValueType.LIST_INTEGER,
                    list_integer_value=int_list,
                )
            msg = f"Unsupported list type with mixed or unsupported elements: {value}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        if isinstance(value, dict):
            return cls(value_type=EnumValueType.DICT, dict_value=json.dumps(value))
        # Fallback for unhandled types
        msg = f"Unsupported type: {type(value).__name__}"  # type: ignore[unreachable]
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=msg,
        )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "value_type": "string",
                    "string_value": "HELLO WORLD",
                    "integer_value": None,
                    "float_value": None,
                    "boolean_value": None,
                    "list_string_value": None,
                    "list_integer_value": None,
                    "dict_value": None,
                },
                {
                    "value_type": "integer",
                    "string_value": None,
                    "integer_value": 42,
                    "float_value": None,
                    "boolean_value": None,
                    "list_string_value": None,
                    "list_integer_value": None,
                    "dict_value": None,
                },
                {
                    "value_type": "boolean",
                    "string_value": None,
                    "integer_value": None,
                    "float_value": None,
                    "boolean_value": True,
                    "list_string_value": None,
                    "list_integer_value": None,
                },
            ],
        }
    )
