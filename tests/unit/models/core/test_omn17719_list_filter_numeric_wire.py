# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Numeric wire-boundary regressions for OMN-17719."""

from __future__ import annotations

from math import inf, nan
from typing import Literal

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_numeric_type import EnumNumericType
from omnibase_core.models.common.model_numeric_value import ModelNumericValue
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_complex_filter import ModelComplexFilter
from omnibase_core.models.core.model_custom_filters import ModelCustomFilters
from omnibase_core.models.core.model_list_filter import ModelListFilter

pytestmark = pytest.mark.unit

Container = Literal["standalone", "complex", "custom"]
_CONTAINERS: tuple[Container, ...] = ("standalone", "complex", "custom")


def _numeric_wire(value: object, value_type: str) -> dict[str, object]:
    return {
        "value_type": "number",
        "number_value": {
            "value": value,
            "value_type": value_type,
            "is_validated": True,
        },
    }


def _adversarial_typed_numeric_wire(
    value: float, value_type: EnumNumericType
) -> dict[str, object]:
    """Build a deliberately invalid legacy instance for downstream rejection proof."""
    return {
        "value_type": "number",
        "number_value": ModelNumericValue.model_construct(
            value=value,
            value_type=value_type,
            is_validated=False,
            source=None,
        ),
    }


_INVALID_WIRES: list[tuple[str, dict[str, object]]] = [
    ("fractional_integer", _numeric_wire(1.5, "integer")),
    ("integer_for_float", _numeric_wire(0, "float")),
    ("positive_infinity", _numeric_wire(inf, "float")),
    ("negative_infinity", _numeric_wire(-inf, "float")),
    ("not_a_number", _numeric_wire(nan, "float")),
    ("non_finite_numeric", _numeric_wire(inf, "numeric")),
    (
        "typed_fractional_integer",
        _adversarial_typed_numeric_wire(1.5, EnumNumericType.INTEGER),
    ),
    (
        "typed_infinity",
        _adversarial_typed_numeric_wire(inf, EnumNumericType.FLOAT),
    ),
    ("lossy_large_integer", _numeric_wire(2**53 + 1, "integer")),
    ("lossy_large_numeric", _numeric_wire(2**53 + 1, "numeric")),
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


@pytest.mark.parametrize("container", _CONTAINERS)
@pytest.mark.parametrize(
    ("case_name", "wire"),
    _INVALID_WIRES,
    ids=[case_name for case_name, _ in _INVALID_WIRES],
)
def test_invalid_numeric_wire_fails_closed_through_every_container(
    container: Container,
    case_name: str,
    wire: dict[str, object],
) -> None:
    del case_name
    with pytest.raises(ValidationError):
        _extract_list_filter(container, wire)


@pytest.mark.parametrize("container", _CONTAINERS)
@pytest.mark.parametrize(
    ("case_name", "wire", "expected"),
    [
        ("integer_zero", _numeric_wire(0, "integer"), 0),
        ("canonical_integer_zero", _numeric_wire(0.0, "integer"), 0),
        ("float_zero", _numeric_wire(0.0, "float"), 0.0),
        ("numeric_float_zero", _numeric_wire(0.0, "numeric"), 0.0),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_finite_numeric_wire_round_trips_with_declared_runtime_type(
    container: Container,
    case_name: str,
    wire: dict[str, object],
    expected: int | float,
) -> None:
    del case_name
    restored = _extract_list_filter(container, wire, round_trip=True)
    actual = restored.values[0].to_value()

    assert type(actual) is type(expected)
    assert actual == expected


@pytest.mark.parametrize("container", _CONTAINERS)
def test_canonical_integer_factory_wire_remains_round_trip_valid(
    container: Container,
) -> None:
    wire = ModelSchemaValue.create_number(0).model_dump(mode="json")

    restored = _extract_list_filter(container, wire, round_trip=True)

    actual = restored.values[0].to_value()
    assert type(actual) is int
    assert actual == 0


@pytest.mark.parametrize("container", _CONTAINERS)
def test_numeric_integer_uses_canonical_float_storage(
    container: Container,
) -> None:
    restored = _extract_list_filter(
        container,
        _numeric_wire(0, "numeric"),
        round_trip=True,
    )

    numeric_value = restored.values[0].number_value
    assert numeric_value is not None
    assert numeric_value.value_type is EnumNumericType.NUMERIC
    assert type(numeric_value.value) is float
    assert numeric_value.value == 0.0
    assert type(restored.values[0].to_value()) is float
