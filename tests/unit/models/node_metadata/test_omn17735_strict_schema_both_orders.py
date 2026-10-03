# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-17735 acceptance check: strict, complete schema under both import orders."""

from __future__ import annotations

import subprocess
import sys

import pytest

_PROBE = """
import importlib
import sys

importlib.import_module(sys.argv[1])
from omnibase_core.models.core.model_node_introspection_response import ModelNodeIntrospectionResponse
from omnibase_core.models.node_metadata.model_node_core_metadata_class import ModelNodeCoreMetadata
from omnibase_core.models.node_metadata.model_node_metadata_info import ModelNodeMetadataInfo

assert ModelNodeCoreMetadata.__pydantic_complete__
assert ModelNodeMetadataInfo.__pydantic_complete__
assert ModelNodeIntrospectionResponse.__pydantic_complete__ is True
assert ModelNodeIntrospectionResponse.model_json_schema()["additionalProperties"] is False
"""


@pytest.mark.unit
@pytest.mark.parametrize(
    "first_module",
    [
        "omnibase_core.models.common.model_numeric_value",
        "omnibase_core.models.core.model_node_introspection_response",
    ],
)
def test_introspection_response_is_complete_and_strict_in_both_orders(
    first_module: str,
) -> None:
    subprocess.run(
        [sys.executable, "-c", _PROBE, first_module],
        check=True,
        text=True,
        capture_output=True,
    )
