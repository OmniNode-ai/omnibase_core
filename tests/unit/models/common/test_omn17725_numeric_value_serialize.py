# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""JSON-mode serialization regressions for OMN-17725."""

from __future__ import annotations

import json

import pytest

from omnibase_core.enums.enum_numeric_type import EnumNumericType
from omnibase_core.models.common.model_numeric_value import ModelNumericValue


@pytest.mark.unit
@pytest.mark.parametrize(
    "numeric",
    [
        pytest.param(ModelNumericValue.from_int(0), id="integer-zero"),
        pytest.param(ModelNumericValue.from_float(0.0), id="float-zero"),
        pytest.param(
            ModelNumericValue(value=1, value_type=EnumNumericType.NUMERIC),
            id="numeric-integer-input",
        ),
    ],
)
def test_serialize_emits_json_safe_canonical_mapping(
    numeric: ModelNumericValue,
) -> None:
    """Serializable output is JSON-safe and round-trips type and value exactly."""
    payload = numeric.serialize()
    encoded = json.dumps(payload, allow_nan=False)
    restored = ModelNumericValue.model_validate_json(encoded)

    assert payload["value_type"] == numeric.value_type.value
    assert restored.value_type is numeric.value_type
    assert restored.value == numeric.value
    assert type(restored.to_python_value()) is type(numeric.to_python_value())
    assert restored.to_python_value() == numeric.to_python_value()


@pytest.mark.unit
def test_plain_model_dump_retains_in_memory_enum_semantics() -> None:
    """The protocol fix does not change the separate in-memory dump API."""
    numeric = ModelNumericValue.from_int(1)

    assert numeric.model_dump()["value_type"] is EnumNumericType.INTEGER
    assert numeric.serialize() == {
        "value": 1.0,
        "value_type": "integer",
        "is_validated": True,
        "source": None,
    }
