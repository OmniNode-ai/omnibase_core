#!/usr/bin/env python3
"""
ONEX Generic Value Model

This module provides a strongly typed generic value model that can represent
different data types in a type-safe manner for validation and testing.
"""

import json
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class EnumValueType(str, Enum):
    """Enumeration of supported value types"""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST_STRING = "list_string"
    LIST_INTEGER = "list_integer"
    DICT = "dict"
    NULL = "null"


class ModelGenericValue(BaseModel):
    """
    Generic value model that can represent different data types in a type-safe manner.

    This model stores a value along with its type information, ensuring type safety
    while allowing flexible value storage for validation and testing scenarios.
    """

    value_type: EnumValueType = Field(description="Type of the stored value")
    string_value: Optional[str] = Field(default=None, description="String value")
    integer_value: Optional[int] = Field(default=None, description="Integer value")
    float_value: Optional[float] = Field(default=None, description="Float value")
    boolean_value: Optional[bool] = Field(default=None, description="Boolean value")
    list_string_value: Optional[List[str]] = Field(
        default=None, description="List of strings"
    )
    list_integer_value: Optional[List[int]] = Field(
        default=None, description="List of integers"
    )
    dict_value: Optional[str] = Field(
        default=None, description="Dictionary value stored as JSON string"
    )

    @validator("string_value")
    def validate_string_value(cls, v, values):
        """Validate string value is set when type is STRING"""
        if values.get("value_type") == EnumValueType.STRING and v is None:
            raise ValueError("string_value must be set when value_type is STRING")
        if values.get("value_type") != EnumValueType.STRING and v is not None:
            raise ValueError(
                "string_value should only be set when value_type is STRING"
            )
        return v

    @validator("integer_value")
    def validate_integer_value(cls, v, values):
        """Validate integer value is set when type is INTEGER"""
        if values.get("value_type") == EnumValueType.INTEGER and v is None:
            raise ValueError("integer_value must be set when value_type is INTEGER")
        if values.get("value_type") != EnumValueType.INTEGER and v is not None:
            raise ValueError(
                "integer_value should only be set when value_type is INTEGER"
            )
        return v

    @validator("float_value")
    def validate_float_value(cls, v, values):
        """Validate float value is set when type is FLOAT"""
        if values.get("value_type") == EnumValueType.FLOAT and v is None:
            raise ValueError("float_value must be set when value_type is FLOAT")
        if values.get("value_type") != EnumValueType.FLOAT and v is not None:
            raise ValueError("float_value should only be set when value_type is FLOAT")
        return v

    @validator("boolean_value")
    def validate_boolean_value(cls, v, values):
        """Validate boolean value is set when type is BOOLEAN"""
        if values.get("value_type") == EnumValueType.BOOLEAN and v is None:
            raise ValueError("boolean_value must be set when value_type is BOOLEAN")
        if values.get("value_type") != EnumValueType.BOOLEAN and v is not None:
            raise ValueError(
                "boolean_value should only be set when value_type is BOOLEAN"
            )
        return v

    @validator("list_string_value")
    def validate_list_string_value(cls, v, values):
        """Validate list string value is set when type is LIST_STRING"""
        if values.get("value_type") == EnumValueType.LIST_STRING and v is None:
            raise ValueError(
                "list_string_value must be set when value_type is LIST_STRING"
            )
        if values.get("value_type") != EnumValueType.LIST_STRING and v is not None:
            raise ValueError(
                "list_string_value should only be set when value_type is LIST_STRING"
            )
        return v

    @validator("list_integer_value")
    def validate_list_integer_value(cls, v, values):
        """Validate list integer value is set when type is LIST_INTEGER"""
        if values.get("value_type") == EnumValueType.LIST_INTEGER and v is None:
            raise ValueError(
                "list_integer_value must be set when value_type is LIST_INTEGER"
            )
        if values.get("value_type") != EnumValueType.LIST_INTEGER and v is not None:
            raise ValueError(
                "list_integer_value should only be set when value_type is LIST_INTEGER"
            )
        return v

    @validator("dict_value")
    def validate_dict_value(cls, v, values):
        """Validate dict value is set when type is DICT"""
        if values.get("value_type") == EnumValueType.DICT and v is None:
            raise ValueError("dict_value must be set when value_type is DICT")
        if values.get("value_type") != EnumValueType.DICT and v is not None:
            raise ValueError("dict_value should only be set when value_type is DICT")
        return v

    def get_python_value(self):
        """Get the actual Python value based on the type"""
        if self.value_type == EnumValueType.STRING:
            return self.string_value
        elif self.value_type == EnumValueType.INTEGER:
            return self.integer_value
        elif self.value_type == EnumValueType.FLOAT:
            return self.float_value
        elif self.value_type == EnumValueType.BOOLEAN:
            return self.boolean_value
        elif self.value_type == EnumValueType.LIST_STRING:
            return self.list_string_value
        elif self.value_type == EnumValueType.LIST_INTEGER:
            return self.list_integer_value
        elif self.value_type == EnumValueType.DICT:
            return json.loads(self.dict_value) if self.dict_value else {}
        elif self.value_type == EnumValueType.NULL:
            return None
        else:
            raise ValueError(f"Unknown value type: {self.value_type}")

    @classmethod
    def from_python_value(cls, value):
        """Create ModelGenericValue from a Python value"""
        if value is None:
            return cls(value_type=EnumValueType.NULL)
        elif isinstance(value, str):
            return cls(value_type=EnumValueType.STRING, string_value=value)
        elif isinstance(value, int):
            return cls(value_type=EnumValueType.INTEGER, integer_value=value)
        elif isinstance(value, float):
            return cls(value_type=EnumValueType.FLOAT, float_value=value)
        elif isinstance(value, bool):
            return cls(value_type=EnumValueType.BOOLEAN, boolean_value=value)
        elif isinstance(value, list):
            if all(isinstance(item, str) for item in value):
                return cls(
                    value_type=EnumValueType.LIST_STRING, list_string_value=value
                )
            elif all(isinstance(item, int) for item in value):
                return cls(
                    value_type=EnumValueType.LIST_INTEGER, list_integer_value=value
                )
            else:
                raise ValueError(
                    f"Unsupported list type with mixed or unsupported elements: {value}"
                )
        elif isinstance(value, dict):
            return cls(value_type=EnumValueType.DICT, dict_value=json.dumps(value))
        else:
            raise ValueError(f"Unsupported value type: {type(value)}")

    class Config:
        json_schema_extra = {
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
            ]
        }
