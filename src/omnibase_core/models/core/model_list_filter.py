# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""List/collection-based custom filter model."""

from __future__ import annotations

from math import isfinite
from typing import Any, cast

from pydantic import Field, field_validator

from omnibase_core.models.common.model_numeric_value import ModelNumericValue
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

from .model_custom_filter_base import ModelCustomFilterBase

_VALUE_FIELD_BY_TYPE = {
    "string": "string_value",
    "number": "number_value",
    "boolean": "boolean_value",
    "null": "null_value",
    "array": "array_value",
    "object": "object_value",
}
_VALUE_FIELDS = frozenset(_VALUE_FIELD_BY_TYPE.values())
_SCHEMA_VALUE_FIELDS = frozenset(ModelSchemaValue.model_fields)
_NUMERIC_VALUE_FIELDS = frozenset(ModelNumericValue.model_fields)
_NUMERIC_TYPES = frozenset({"integer", "float", "numeric"})


def _invalid_wire(reason: str) -> ValueError:
    return ValueError(f"Invalid ModelSchemaValue wire value: {reason}")


def _validate_numeric_wire(value: object) -> None:
    numeric_value: object
    numeric_type: object
    if isinstance(value, ModelNumericValue):
        numeric_value = value.value
        numeric_type = value.value_type.value
    else:
        if not isinstance(value, dict):
            raise _invalid_wire("number_value must be a ModelNumericValue mapping")

        wire = cast(dict[object, object], value)
        unknown_fields = set(wire) - _NUMERIC_VALUE_FIELDS
        if unknown_fields:
            raise _invalid_wire("number_value contains unknown fields")
        if "value" not in wire or "value_type" not in wire:
            raise _invalid_wire("number_value is missing a required field")

        numeric_value = wire["value"]
        numeric_type = wire["value_type"]
        if "is_validated" in wire and not isinstance(wire["is_validated"], bool):
            raise _invalid_wire("number_value.is_validated must be a bool")
        if (
            "source" in wire
            and wire["source"] is not None
            and not isinstance(wire["source"], str)
        ):
            raise _invalid_wire("number_value.source must be a string or null")

    if isinstance(numeric_value, bool) or not isinstance(numeric_value, (int, float)):
        raise _invalid_wire("number_value.value must be an int or float")
    if not isinstance(numeric_type, str) or numeric_type not in _NUMERIC_TYPES:
        raise _invalid_wire("number_value.value_type is invalid")
    if isinstance(numeric_value, float) and not isfinite(numeric_value):
        raise _invalid_wire("number_value.value must be finite")

    if isinstance(numeric_value, int):
        if numeric_type == "float":
            raise _invalid_wire("float number_value must contain a float")
        # ModelNumericValue owns canonical float storage. INTEGER restores an int
        # on read; NUMERIC intentionally retains the canonical float value.
        try:
            stored_value = float(numeric_value)
        except OverflowError as exc:
            raise _invalid_wire(
                f"{numeric_type} value exceeds canonical storage"
            ) from exc
        if not isfinite(stored_value) or int(stored_value) != numeric_value:
            raise _invalid_wire(f"{numeric_type} value loses precision in storage")
    elif numeric_type == "integer" and not numeric_value.is_integer():
        # Canonical integer JSON contains an integral float because the owned
        # ModelNumericValue storage field is float; fractions remain invalid.
        raise _invalid_wire("integer number_value cannot contain a fraction")


def _validate_schema_value_wire(value: object) -> None:
    if isinstance(value, ModelSchemaValue):
        wire = cast(dict[object, object], value.model_dump())
    elif isinstance(value, dict):
        wire = cast(dict[object, object], value)
    else:
        raise _invalid_wire("nested values must be ModelSchemaValue mappings")

    unknown_fields = set(wire) - _SCHEMA_VALUE_FIELDS
    if unknown_fields:
        raise _invalid_wire("unknown fields are not allowed")

    value_type = wire.get("value_type")
    if not isinstance(value_type, str) or value_type not in _VALUE_FIELD_BY_TYPE:
        raise _invalid_wire("value_type is missing or unknown")

    selected_field = _VALUE_FIELD_BY_TYPE[value_type]
    if selected_field not in wire:
        raise _invalid_wire(f"{selected_field} is required for {value_type}")
    if any(
        wire.get(field_name) is not None
        for field_name in _VALUE_FIELDS - {selected_field}
    ):
        raise _invalid_wire("non-selected value fields must be absent or null")

    selected_value = wire[selected_field]
    if value_type == "string":
        if not isinstance(selected_value, str):
            raise _invalid_wire("string_value must be a string")
    elif value_type == "number":
        _validate_numeric_wire(selected_value)
    elif value_type == "boolean":
        if not isinstance(selected_value, bool):
            raise _invalid_wire("boolean_value must be a bool")
    elif value_type == "null":
        if selected_value is not True:
            raise _invalid_wire("null_value must be true")
    elif value_type == "array":
        if not isinstance(selected_value, list):
            raise _invalid_wire("array_value must be a list")
        for item in cast(list[object], selected_value):
            _validate_schema_value_wire(item)
    else:
        if not isinstance(selected_value, dict):
            raise _invalid_wire("object_value must be a mapping")
        object_value = cast(dict[object, object], selected_value)
        if any(not isinstance(key, str) for key in object_value):
            raise _invalid_wire("object_value keys must be strings")
        for item in object_value.values():
            _validate_schema_value_wire(item)


class ModelListFilter(ModelCustomFilterBase):
    """List/collection-based custom filter.

    Uses ModelSchemaValue for type-safe list values.
    """

    filter_type: str = Field(default="list", description="Filter type identifier")
    values: list[ModelSchemaValue] = Field(
        default=..., description="List of values to match (type-safe)"
    )
    match_all: bool = Field(default=False, description="Must match all values (vs any)")
    exclude: bool = Field(default=False, description="Exclude matching items")

    @field_validator("values", mode="before")
    @classmethod
    def convert_values_to_schema(cls, v: Any) -> object:
        """Convert values to ModelSchemaValue for type safety."""
        if not isinstance(v, list):
            return v

        converted: list[ModelSchemaValue] = []
        for item in cast(list[object], v):
            if isinstance(item, ModelSchemaValue):
                _validate_schema_value_wire(item)
                converted.append(item)
                continue

            if isinstance(item, dict) and "value_type" in item:
                _validate_schema_value_wire(item)
                converted.append(ModelSchemaValue.model_validate(item))
                continue

            converted.append(ModelSchemaValue.from_value(item))

        return converted
