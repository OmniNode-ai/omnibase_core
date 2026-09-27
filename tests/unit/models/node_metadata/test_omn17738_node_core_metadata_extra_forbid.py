# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fail-closed wire-boundary coverage for node core metadata."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType
from omnibase_core.models.core.model_node_introspection_response import (
    ModelNodeIntrospectionResponse,
)
from omnibase_core.models.node_metadata.model_node_core_metadata_class import (
    ModelNodeCoreMetadata,
)


def _core_payload() -> dict[str, object]:
    return {
        "node_display_name": "strict-node",
        "node_type": EnumMetadataNodeType.FUNCTION.value,
    }


@pytest.mark.unit
def test_node_core_metadata_rejects_unknown_mapping_and_json_keys() -> None:
    """Unknown wire keys must not be silently discarded at this typed boundary."""
    payload = _core_payload()
    payload["unexpected"] = True

    with pytest.raises(ValidationError) as mapping_error:
        ModelNodeCoreMetadata.model_validate(payload)
    with pytest.raises(ValidationError) as json_error:
        ModelNodeCoreMetadata.model_validate_json(json.dumps(payload))

    for error in (*mapping_error.value.errors(), *json_error.value.errors()):
        assert error["type"] == "extra_forbidden"
        assert error["loc"] == ("unexpected",)


@pytest.mark.unit
def test_node_core_and_nested_response_schemas_reject_unknown_properties() -> None:
    """The strict core contract composes into the strict introspection response."""
    with pytest.raises(ValidationError) as response_error:
        ModelNodeIntrospectionResponse.model_validate({"unexpected": True})

    assert ModelNodeCoreMetadata.model_json_schema()["additionalProperties"] is False
    assert (
        ModelNodeIntrospectionResponse.model_json_schema()["additionalProperties"]
        is False
    )
    assert any(
        error["type"] == "extra_forbidden" and error["loc"] == ("unexpected",)
        for error in response_error.value.errors()
    )
