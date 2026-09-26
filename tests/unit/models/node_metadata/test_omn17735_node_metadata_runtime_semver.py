# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression coverage for the node-metadata SemVer runtime boundary."""

from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType
from omnibase_core.models.node_metadata.model_node_core_metadata_class import (
    ModelNodeCoreMetadata,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    "first_module",
    [
        "omnibase_core.models.common.model_numeric_value",
        "omnibase_core.models.core.model_node_introspection_response",
    ],
)
def test_node_introspection_schema_is_complete_in_both_fresh_import_orders(
    first_module: str,
) -> None:
    """A valid import order must not leave the nested SemVer graph incomplete."""
    probe = """
import importlib
import sys

importlib.import_module(sys.argv[1])
from omnibase_core.models.core.model_node_introspection_response import ModelNodeIntrospectionResponse
from omnibase_core.models.node_metadata.model_node_core_metadata_class import ModelNodeCoreMetadata
from omnibase_core.models.node_metadata.model_node_metadata_info import ModelNodeMetadataInfo

assert ModelNodeCoreMetadata.__pydantic_complete__
assert ModelNodeMetadataInfo.__pydantic_complete__
assert ModelNodeIntrospectionResponse.__pydantic_complete__
assert ModelNodeIntrospectionResponse.model_json_schema()["type"] == "object"
"""
    subprocess.run(
        [sys.executable, "-c", probe, first_module],
        check=True,
        text=True,
        capture_output=True,
    )


@pytest.mark.unit
def test_node_core_metadata_validates_and_round_trips_typed_semver() -> None:
    """The repaired runtime import preserves the existing typed SemVer wire contract."""
    payload: dict[str, object] = {
        "node_display_name": "test-node",
        "node_type": EnumMetadataNodeType.FUNCTION.value,
        "version": {"major": 1, "minor": 2, "patch": 3},
    }

    metadata = ModelNodeCoreMetadata.model_validate(payload)
    restored = ModelNodeCoreMetadata.model_validate_json(metadata.model_dump_json())

    assert str(metadata.version) == "1.2.3"
    assert restored == metadata


@pytest.mark.unit
def test_node_metadata_schema_rebuild_is_repeatedly_concurrent_and_stable() -> None:
    """Concurrent callers observe a complete immutable schema graph."""
    from omnibase_core.models.core.model_node_introspection_response import (
        ModelNodeIntrospectionResponse,
    )
    from omnibase_core.models.node_metadata.model_node_metadata_info import (
        ModelNodeMetadataInfo,
    )

    def read_schema() -> tuple[bool, bool, bool, str]:
        schema = ModelNodeIntrospectionResponse.model_json_schema()
        return (
            ModelNodeCoreMetadata.__pydantic_complete__,
            ModelNodeMetadataInfo.__pydantic_complete__,
            ModelNodeIntrospectionResponse.__pydantic_complete__,
            schema["type"],
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        observations = list(executor.map(lambda _: read_schema(), range(16)))

    assert observations == [(True, True, True, "object")] * 16
