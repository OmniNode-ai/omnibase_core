# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unknown-key contract regressions for OMN-17724."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_numeric_type import EnumNumericType
from omnibase_core.models.common.model_numeric_value import ModelNumericValue
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


@pytest.mark.unit
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            {"value": 1, "value_type": "integer", "unexpected": "discarded"},
            id="mapping",
        ),
        pytest.param(
            '{"value":1,"value_type":"integer","unexpected":"discarded"}',
            id="json",
        ),
    ],
)
def test_unknown_numeric_fields_fail_closed(payload: object) -> None:
    """Mapping and JSON entry points cannot silently discard unknown keys."""
    with pytest.raises(ValidationError):
        if isinstance(payload, str):
            ModelNumericValue.model_validate_json(payload)
        else:
            ModelNumericValue.model_validate(payload)


@pytest.mark.unit
def test_nested_schema_value_rejects_unknown_numeric_fields() -> None:
    """The canonical nested owner enforces the same unknown-key boundary."""
    with pytest.raises(ValidationError):
        ModelSchemaValue.model_validate(
            {
                "value_type": "number",
                "number_value": {
                    "value": 1,
                    "value_type": "integer",
                    "unexpected": "discarded",
                },
            }
        )


@pytest.mark.unit
def test_canonical_numeric_mapping_and_assignment_remain_supported() -> None:
    """The config contraction preserves the declared mutable DTO contract."""
    numeric = ModelNumericValue.model_validate(
        {
            "value": 0,
            "value_type": "integer",
            "is_validated": True,
            "source": None,
        }
    )

    numeric.value = 1

    assert numeric.value == 1.0
    assert numeric.value_type is EnumNumericType.INTEGER
    assert numeric.model_json_schema()["additionalProperties"] is False
