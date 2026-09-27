# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Strict ModelSchemaValue wire-boundary regressions for OMN-17715."""

from __future__ import annotations

from typing import Literal, cast

import pytest
from pydantic import ValidationError

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_complex_filter import ModelComplexFilter
from omnibase_core.models.core.model_custom_filters import ModelCustomFilters
from omnibase_core.models.core.model_list_filter import ModelListFilter

pytestmark = pytest.mark.unit

Container = Literal["standalone", "complex", "custom"]

_CONTAINERS: tuple[Container, ...] = ("standalone", "complex", "custom")

_INVALID_WIRES: list[tuple[str, dict[str, object]]] = [
    (
        "cross_variant",
        {
            "value_type": "string",
            "string_value": "ok",
            "boolean_value": False,
        },
    ),
    (
        "boolean_string",
        {"value_type": "boolean", "boolean_value": "false"},
    ),
    (
        "boolean_integer",
        {"value_type": "boolean", "boolean_value": 1},
    ),
    (
        "null_integer",
        {"value_type": "null", "null_value": 1},
    ),
    (
        "number_boolean",
        {
            "value_type": "number",
            "number_value": {
                "value": True,
                "value_type": "integer",
                "is_validated": True,
            },
        },
    ),
    (
        "nested_unknown",
        {
            "value_type": "object",
            "object_value": {
                "key": {
                    "value_type": "string",
                    "string_value": "value",
                    "unknown": True,
                }
            },
        },
    ),
    (
        "nested_missing_selected",
        {
            "value_type": "array",
            "array_value": [{"value_type": "string"}],
        },
    ),
    (
        "nested_cross_variant",
        {
            "value_type": "array",
            "array_value": [
                {
                    "value_type": "string",
                    "string_value": "value",
                    "boolean_value": False,
                }
            ],
        },
    ),
]

_VALID_VALUES: list[object] = [
    "",
    0,
    0.0,
    False,
    None,
    [],
    {},
    [False, 0, ""],
    {"false": False, "zero": 0, "empty": ""},
]


def _extract_list_filter(
    container: Container,
    wire: dict[str, object],
    *,
    round_trip: bool = False,
) -> ModelListFilter:
    if container == "standalone":
        model = ModelListFilter.model_validate({"values": [wire]})
        if round_trip:
            model = ModelListFilter.model_validate_json(model.model_dump_json())
        return model

    if container == "complex":
        complex_filter = ModelComplexFilter.model_validate(
            {
                "filter_type": "complex",
                "sub_filters": [{"filter_type": "list", "values": [wire]}],
            }
        )
        if round_trip:
            complex_filter = ModelComplexFilter.model_validate_json(
                complex_filter.model_dump_json()
            )
        complex_list_filter = complex_filter.sub_filters[0]
        assert isinstance(complex_list_filter, ModelListFilter)
        return complex_list_filter

    custom_filters = ModelCustomFilters.model_validate(
        {
            "filters": {
                "selected": {"filter_type": "list", "values": [wire]},
            }
        }
    )
    if round_trip:
        custom_filters = ModelCustomFilters.model_validate_json(
            custom_filters.model_dump_json()
        )
    custom_list_filter = custom_filters.filters["selected"]
    assert isinstance(custom_list_filter, ModelListFilter)
    return custom_list_filter


def _assert_json_type_and_value(actual: object, expected: object) -> None:
    assert type(actual) is type(expected)
    assert actual == expected
    if isinstance(expected, list):
        assert isinstance(actual, list)
        for actual_item, expected_item in zip(actual, expected, strict=True):
            _assert_json_type_and_value(actual_item, expected_item)
    elif isinstance(expected, dict):
        assert isinstance(actual, dict)
        assert actual.keys() == expected.keys()
        for key, expected_item in expected.items():
            _assert_json_type_and_value(actual[key], expected_item)


@pytest.mark.parametrize("container", _CONTAINERS)
@pytest.mark.parametrize(
    ("case_name", "wire"),
    _INVALID_WIRES,
    ids=[case_name for case_name, _ in _INVALID_WIRES],
)
def test_malformed_typed_wire_fails_closed_through_every_container(
    container: Container,
    case_name: str,
    wire: dict[str, object],
) -> None:
    del case_name
    with pytest.raises(ValidationError):
        _extract_list_filter(container, wire)


@pytest.mark.parametrize("container", _CONTAINERS)
@pytest.mark.parametrize("raw_value", _VALID_VALUES, ids=repr)
def test_valid_falsy_wire_round_trips_with_exact_type_and_value(
    container: Container,
    raw_value: object,
) -> None:
    wire = cast(
        dict[str, object],
        ModelSchemaValue.from_value(raw_value).model_dump(mode="json"),
    )

    restored = _extract_list_filter(container, wire, round_trip=True)

    _assert_json_type_and_value(restored.values[0].to_value(), raw_value)


def test_discriminator_free_mapping_remains_a_raw_object_value() -> None:
    model = ModelListFilter.model_validate(
        {"values": [{"boolean_value": "raw", "unknown": False}]}
    )

    assert model.values[0].to_value() == {
        "boolean_value": "raw",
        "unknown": False,
    }
