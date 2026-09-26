# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical numeric construction and assignment regressions for OMN-17720."""

from __future__ import annotations

from collections.abc import Callable
from math import inf, nan

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_numeric_type import EnumNumericType
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_numeric_value import ModelNumericValue
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

NUMERIC_VALIDATION_ERRORS = (ModelOnexError, ValidationError)


@pytest.mark.unit
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            {"value": "1", "value_type": EnumNumericType.INTEGER},
            id="integer-string",
        ),
        pytest.param(
            {"value": True, "value_type": EnumNumericType.INTEGER},
            id="integer-bool",
        ),
        pytest.param(
            {"value": 1.5, "value_type": EnumNumericType.INTEGER},
            id="fractional-integer",
        ),
        pytest.param(
            {"value": 1, "value_type": EnumNumericType.FLOAT},
            id="int-as-float",
        ),
        pytest.param(
            {"value": nan, "value_type": EnumNumericType.FLOAT},
            id="nan",
        ),
        pytest.param(
            {"value": inf, "value_type": EnumNumericType.FLOAT},
            id="positive-infinity",
        ),
        pytest.param(
            {"value": -inf, "value_type": EnumNumericType.NUMERIC},
            id="negative-infinity",
        ),
        pytest.param(
            {"value": 2**53 + 1, "value_type": EnumNumericType.INTEGER},
            id="lossy-integer",
        ),
        pytest.param(
            {"value": 2**53 + 1, "value_type": EnumNumericType.NUMERIC},
            id="lossy-numeric",
        ),
    ],
)
def test_raw_numeric_mappings_reject_coercion_and_invalid_storage(
    payload: dict[str, object],
) -> None:
    """Raw mappings fail before Pydantic can coerce or truncate the value."""
    with pytest.raises(NUMERIC_VALIDATION_ERRORS):
        ModelNumericValue.model_validate(payload)


@pytest.mark.unit
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param('{"value":"1","value_type":"integer"}', id="json-string"),
        pytest.param('{"value":true,"value_type":"integer"}', id="json-boolean"),
        pytest.param('{"value":1.5,"value_type":"integer"}', id="json-fraction"),
        pytest.param('{"value":1,"value_type":"float"}', id="json-int-as-float"),
    ],
)
def test_json_numeric_inputs_apply_the_same_strict_boundary(payload: str) -> None:
    """JSON parsing must not create a compatibility coercion path."""
    with pytest.raises(NUMERIC_VALIDATION_ERRORS):
        ModelNumericValue.model_validate_json(payload)


@pytest.mark.unit
def test_factories_reject_runtime_values_outside_their_typed_contracts() -> None:
    """Factories preserve raw provenance until canonical validation runs."""
    invalid_calls: tuple[Callable[[], ModelNumericValue], ...] = (
        lambda: ModelNumericValue.from_int(True),
        lambda: ModelNumericValue.from_float(1),
        lambda: ModelNumericValue.from_numeric(True),
        lambda: ModelNumericValue.from_float(inf),
        lambda: ModelNumericValue.from_int(2**53 + 1),
    )

    for call in invalid_calls:
        with pytest.raises(NUMERIC_VALIDATION_ERRORS):
            call()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("model", "expected_type", "expected_value_type"),
    [
        pytest.param(
            ModelNumericValue.from_int(0), int, EnumNumericType.INTEGER, id="integer"
        ),
        pytest.param(
            ModelNumericValue.from_float(0.0),
            float,
            EnumNumericType.FLOAT,
            id="float",
        ),
        pytest.param(
            ModelNumericValue(value=0, value_type=EnumNumericType.NUMERIC),
            float,
            EnumNumericType.NUMERIC,
            id="numeric",
        ),
    ],
)
def test_canonical_zero_and_json_round_trip_preserve_logical_type(
    model: ModelNumericValue,
    expected_type: type[int] | type[float],
    expected_value_type: EnumNumericType,
) -> None:
    """Valid falsy values preserve their discriminator and Python result type."""
    restored = ModelNumericValue.model_validate_json(model.model_dump_json())

    assert restored.value == 0.0
    assert restored.value_type is expected_value_type
    assert type(restored.to_python_value()) is expected_type


def _assert_failed_assignment_is_transactional(
    model: ModelNumericValue, field: str, invalid_value: object
) -> None:
    before_mapping = model.model_dump()
    before_json = model.model_dump_json()

    with pytest.raises(NUMERIC_VALIDATION_ERRORS):
        setattr(model, field, invalid_value)

    assert model.model_dump() == before_mapping
    assert model.model_dump_json() == before_json


@pytest.mark.unit
@pytest.mark.parametrize("invalid_value", [2, "2", True, nan, inf, -inf])
def test_invalid_value_assignment_is_transactional(invalid_value: object) -> None:
    """A rejected FLOAT mutation leaves both object state and JSON unchanged."""
    _assert_failed_assignment_is_transactional(
        ModelNumericValue.from_float(1.5), "value", invalid_value
    )


@pytest.mark.unit
@pytest.mark.parametrize("invalid_value", [1.5, 2**53 + 1, nan, inf, True, "2"])
def test_invalid_integer_assignment_is_transactional(invalid_value: object) -> None:
    """INTEGER assignment cannot coerce, truncate, or introduce non-finite state."""
    _assert_failed_assignment_is_transactional(
        ModelNumericValue.from_int(1), "value", invalid_value
    )


@pytest.mark.unit
@pytest.mark.parametrize("invalid_value", [True, 2**53 + 1, inf])
def test_invalid_numeric_assignment_is_transactional(invalid_value: object) -> None:
    """NUMERIC assignment rejects booleans, precision loss, and non-finite state."""
    _assert_failed_assignment_is_transactional(
        ModelNumericValue(value=1, value_type=EnumNumericType.NUMERIC),
        "value",
        invalid_value,
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("model", "new_type"),
    [
        pytest.param(
            ModelNumericValue.from_float(1.5),
            EnumNumericType.INTEGER,
            id="fractional-float-to-integer",
        ),
        pytest.param(
            ModelNumericValue.from_float(1.0),
            "not-a-numeric-type",
            id="unknown-discriminator",
        ),
    ],
)
def test_discriminator_assignment_is_transactional(
    model: ModelNumericValue, new_type: object
) -> None:
    """A discriminator cannot be retagged independently from its value authority."""
    _assert_failed_assignment_is_transactional(model, "value_type", new_type)


@pytest.mark.unit
def test_compatible_discriminator_assignment_remains_supported() -> None:
    """A finite candidate may be retagged when its complete mapping proves parity."""
    integral_float = ModelNumericValue.from_float(1.0)
    integer = ModelNumericValue.from_int(2)
    floating = ModelNumericValue.from_float(2.5)

    integral_float.value_type = EnumNumericType.INTEGER
    integer.value_type = EnumNumericType.FLOAT
    floating.value_type = EnumNumericType.NUMERIC

    for model, expected in (
        (integral_float, 1),
        (integer, 2.0),
        (floating, 2.5),
    ):
        restored = ModelNumericValue.model_validate_json(model.model_dump_json())
        actual = restored.to_python_value()

        assert restored.value_type is model.value_type
        assert type(actual) is type(expected)
        assert actual == expected


@pytest.mark.unit
def test_valid_assignment_and_schema_value_round_trip_remain_supported() -> None:
    """Sanctioned mutation retains canonical storage and nested JSON parity."""
    integer = ModelNumericValue.from_int(1)
    floating = ModelNumericValue.from_float(1.5)
    numeric = ModelNumericValue(value=1, value_type=EnumNumericType.NUMERIC)

    integer.value = 2
    floating.value = 2.5
    numeric.value = 2
    integer.source = "updated"

    for value in (integer, floating, numeric):
        nested = ModelSchemaValue(value_type="number", number_value=value)
        restored = ModelSchemaValue.model_validate_json(nested.model_dump_json())

        assert restored.number_value is not None
        assert restored.number_value.value == value.value
        assert restored.number_value.value_type is value.value_type

    assert integer.to_python_value() == 2
    assert type(integer.to_python_value()) is int
    assert floating.to_python_value() == 2.5
    assert type(floating.to_python_value()) is float
    assert numeric.to_python_value() == 2.0
    assert type(numeric.to_python_value()) is float
