# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Required-version regressions for ``ModelIntrospectionNodeInfo``."""

import json

import pytest
from pydantic import ValidationError

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_introspection_node_info import (
    ModelIntrospectionNodeInfo,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


def _payload(node_version: object) -> dict[str, object]:
    return {
        "node_name": "node_example",
        "node_version": node_version,
        "description": "Example node",
        "tool_type": "compute",
    }


@pytest.mark.unit
def test_constructor_preserves_required_typed_version() -> None:
    """A typed version remains the sole authority at direct construction."""
    version = ModelSemVer(major=2, minor=4, patch=6)

    node_info = ModelIntrospectionNodeInfo(
        node_name="node_example",
        node_version=version,
        description="Example node",
        tool_type="compute",
    )

    assert node_info.node_version is version
    assert "node_version" in ModelIntrospectionNodeInfo.model_json_schema()["required"]
    assert ModelIntrospectionNodeInfo.model_fields["node_version"].is_required()


@pytest.mark.unit
def test_model_validate_accepts_complete_mapping_and_semver_string() -> None:
    """Sanctioned external forms resolve through the canonical SemVer contract."""
    mapping_result = ModelIntrospectionNodeInfo.model_validate(
        _payload({"major": 3, "minor": 2, "patch": 1})
    )
    string_result = ModelIntrospectionNodeInfo.model_validate(
        _payload("4.5.6-alpha.1+build.7")
    )

    assert mapping_result.node_version == ModelSemVer(major=3, minor=2, patch=1)
    assert string_result.node_version == ModelSemVer(
        major=4,
        minor=5,
        patch=6,
        prerelease=("alpha", 1),
        build=("build", "7"),
    )


@pytest.mark.unit
def test_json_round_trip_preserves_explicit_version() -> None:
    """JSON validation and serialization never invent or discard version data."""
    node_info = ModelIntrospectionNodeInfo.model_validate_json(
        json.dumps(_payload({"major": 7, "minor": 8, "patch": 9}))
    )

    restored = ModelIntrospectionNodeInfo.model_validate_json(
        node_info.model_dump_json()
    )

    assert restored == node_info
    assert restored.node_version == ModelSemVer(major=7, minor=8, patch=9)


@pytest.mark.unit
@pytest.mark.parametrize(
    "malformed_version",
    [None, 1, 1.5, True, [], [1, 2, 3], {}, {"major": 1}, {"major": 1, "minor": 2}],
)
def test_malformed_version_fails_closed(malformed_version: object) -> None:
    """Malformed or partial values cannot become an invented 1.0.0 version."""
    with pytest.raises(ValidationError, match="node_version"):
        ModelIntrospectionNodeInfo.model_validate(_payload(malformed_version))


@pytest.mark.unit
def test_missing_and_invalid_string_versions_fail_closed() -> None:
    """The required field and canonical string parser both reject absent authority."""
    payload = _payload(ModelSemVer(major=1, minor=2, patch=3))
    del payload["node_version"]

    with pytest.raises(ValidationError, match="node_version"):
        ModelIntrospectionNodeInfo.model_validate(payload)

    with pytest.raises(ModelOnexError, match="Invalid semantic version format"):
        ModelIntrospectionNodeInfo.model_validate(_payload("not-a-version"))
