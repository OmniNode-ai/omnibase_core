from typing import Any, Dict, Generic, List

from pydantic import Field, field_validator

from omnibase_core.enums.enum_value_type import EnumValueType

#!/usr/bin/env python3
"""
ONEX Generic Value Model

This module provides a strongly typed generic value model that can represent
different data types in a type-safe manner for validation and testing.
"""

import json
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    def validate_string_value(cls, v, info):
        """Validate string value is set when type is STRING"""
        data = info.data if info else {}
        if data.get("value_type") == EnumValueType.STRING and v is None:
            msg = "string_value must be set when value_type is STRING"
            raise ValueError(msg)
        if data.get("value_type") != EnumValueType.STRING and v is not None:
            msg = "string_value should only be set when value_type is STRING"
            raise ValueError(
                msg,
            )
        return v

    @field_validator("integer_value")
    @classmethod
    def validate_integer_value(cls, v, info):
        """Validate integer value is set when type is INTEGER"""
        data = info.data if info else {}
        if data.get("value_type") == EnumValueType.INTEGER and v is None:
            msg = "integer_value must be set when value_type is INTEGER"
            raise ValueError(msg)
        if data.get("value_type") != EnumValueType.INTEGER and v is not None:
            msg = "integer_value should only be set when value_type is INTEGER"
            raise ValueError(
                msg,
            )
        return v

    @field_validator("float_value")
    @classmethod
    def validate_float_value(cls, v, info):
        """Validate float value is set when type is FLOAT"""
        data = info.data if info else {}
        if data.get("value_type") == EnumValueType.FLOAT and v is None:
            msg = "float_value must be set when value_type is FLOAT"
            raise ValueError(msg)
        if data.get("value_type") != EnumValueType.FLOAT and v is not None:
            msg = "float_value should only be set when value_type is FLOAT"
            raise ValueError(msg)
        return v

    @field_validator("boolean_value")
    @classmethod
    def validate_boolean_value(cls, v, info):
        """Validate boolean value is set when type is BOOLEAN"""
        data = info.data if info else {}
        if data.get("value_type") == EnumValueType.BOOLEAN and v is None:
            msg = "boolean_value must be set when value_type is BOOLEAN"
            raise ValueError(msg)
        if data.get("value_type") != EnumValueType.BOOLEAN and v is not None:
            msg = "boolean_value should only be set when value_type is BOOLEAN"
            raise ValueError(
                msg,
            )
        return v

    @field_validator("list_string_value")
    @classmethod
    def validate_list_string_value(cls, v, info):
        """Validate list[Any]string value is set when type is LIST_STRING"""
        data = info.data if info else {}
        if data.get("value_type") == EnumValueType.LIST_STRING and v is None:
            msg = "list_string_value must be set when value_type is LIST_STRING"
            raise ValueError(
                msg,
            )
        if data.get("value_type") != EnumValueType.LIST_STRING and v is not None:
            msg = "list_string_value should only be set when value_type is LIST_STRING"
            raise ValueError(
                msg,
            )
        return v

    @field_validator("list_integer_value")
    @classmethod
    def validate_list_integer_value(cls, v, info):
        """Validate list[Any]integer value is set when type is LIST_INTEGER"""
        data = info.data if info else {}
        if data.get("value_type") == EnumValueType.LIST_INTEGER and v is None:
            msg = "list_integer_value must be set when value_type is LIST_INTEGER"
            raise ValueError(
                msg,
            )
        if data.get("value_type") != EnumValueType.LIST_INTEGER and v is not None:
            msg = (
                "list_integer_value should only be set when value_type is LIST_INTEGER"
            )
            raise ValueError(
                msg,
            )
        return v

    @field_validator("dict_value")
    @classmethod
    def validate_dict_value(cls, v, info):
        """Validate dict[str, Any]value is set when type is DICT"""
        data = info.data if info else {}
        if data.get("value_type") == EnumValueType.DICT and v is None:
            msg = "dict_value must be set when value_type is DICT"
            raise ValueError(msg)
        if data.get("value_type") != EnumValueType.DICT and v is not None:
            msg = "dict_value should only be set when value_type is DICT"
            raise ValueError(msg)
        return v

    def get_python_value(self):
        """Get the actual Python value based on the type"""
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
        msg = f"Unknown value type: {self.value_type}"
        raise ValueError(msg)

    @classmethod
    def from_python_value(cls, value):
        """Create ModelGenericValue from a Python value"""
        if value is None:
            return cls(value_type=EnumValueType.NULL)
        if isinstance(value, str):
            return cls(value_type=EnumValueType.STRING, string_value=value)
        if isinstance(value, int):
            return cls(value_type=EnumValueType.INTEGER, integer_value=value)
        if isinstance(value, float):
            return cls(value_type=EnumValueType.FLOAT, float_value=value)
        if isinstance(value, bool):
            return cls(value_type=EnumValueType.BOOLEAN, boolean_value=value)
        if isinstance(value, list):
            if all(isinstance(item, str) for item in value):
                return cls(
                    value_type=EnumValueType.LIST_STRING,
                    list_string_value=value,
                )
            if all(isinstance(item, int) for item in value):
                return cls(
                    value_type=EnumValueType.LIST_INTEGER,
                    list_integer_value=value,
                )
            msg = (
                f"Unsupported list[Any]type with mixed or unsupported elements: {value}"
            )
            raise ValueError(
                msg,
            )
        if isinstance(value, dict):
            return cls(value_type=EnumValueType.DICT, dict_value=json.dumps(value))
        msg = f"Unsupported value type: {type(value)}"
        raise ValueError(msg)

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
