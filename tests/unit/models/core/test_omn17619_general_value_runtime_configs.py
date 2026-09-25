# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Grouped strict-boundary regressions for OMN-17619's mutable DTO families."""

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.models.core.model_feature_flags import ModelFeatureFlags
from omnibase_core.models.core.model_optional_string import ModelOptionalString
from omnibase_core.models.core.model_serializable_dict import ModelSerializableDict
from omnibase_core.models.core.model_string_list import ModelStringList


@pytest.mark.unit
@pytest.mark.parametrize(
    ("model_type", "payload"),
    [
        (ModelOptionalString, {"value": "x"}),
        (ModelSerializableDict, {"data": {"key": "value"}}),
        (ModelStringList, {"items": ["a"]}),
        (ModelFeatureFlags, {"flags": {"feature": True}}),
    ],
)
def test_mutable_value_models_reject_unknown_wire_fields(
    model_type: type[BaseModel], payload: dict[str, object]
) -> None:
    """The ratchet is fail-closed without changing mutable model behavior."""
    with pytest.raises(ValidationError, match="extra_forbidden"):
        model_type.model_validate({**payload, "unexpected": True})


@pytest.mark.unit
def test_mutable_collection_models_retain_round_trip_and_mutation() -> None:
    """Strict input validation leaves existing mutable collection APIs intact."""
    strings = ModelStringList.model_validate_json('{"items":["a"]}')
    values = ModelSerializableDict.model_validate_json('{"data":{"a":"1"}}')
    flags = ModelFeatureFlags.model_validate_json('{"flags":{"a":true}}')

    strings.add("b")
    values.set_value("b", "2")
    flags.enable("b")

    assert ModelStringList.model_validate_json(strings.model_dump_json()).items == [
        "a",
        "b",
    ]
    assert ModelSerializableDict.model_validate_json(values.model_dump_json()).data == {
        "a": "1",
        "b": "2",
    }
    assert ModelFeatureFlags.model_validate_json(flags.model_dump_json()).is_enabled(
        "b"
    )
