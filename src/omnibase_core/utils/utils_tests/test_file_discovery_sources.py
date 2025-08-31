# === OmniNode:Metadata ===
# metadata_version: 0.1.0
# protocol_version: 0.1.0
# owner: OmniNode Team
# copyright: OmniNode Team
# schema_version: 0.1.0
# name: test_file_discovery_sources.py
# version: 1.0.0
# uuid: db6a7322-47cd-4515-838b-2ab65c680954
# author: OmniNode Team
# created_at: 2025-05-21T12:41:40.172812
# last_modified_at: 2025-05-21T16:42:46.051763
# description: Stamped by ToolPython
# state_contract: state_contract://default
# lifecycle: active
# hash: 39f5e50c571035f226c63f60bb9e812e4ea5309459717c44aca8dd2f7bfde182
# entrypoint: python@test_file_discovery_sources.py
# runtime_language_hint: python>=3.11
# namespace: onex.stamped.test_file_discovery_sources
# meta_type: tool
# === /OmniNode:Metadata ===


"""
Protocol-first, fixture-injected, registry-driven tests for file discovery sources.
Compliant with ONEX testing policy (see docs/testing.md).
"""

from pathlib import Path
from typing import Any

import pytest

from omnibase_core.core.error_codes import CoreErrorCode, OnexError
from omnibase_core.utils.directory_traverser import DirectoryTraverser
from omnibase_core.utils.hybrid_file_discovery_source import HybridFileDiscoverySource
from omnibase_core.utils.tree_file_discovery_source import TreeFileDiscoverySource
from omnibase_core.utils.utils_tests.utils_test_file_discovery_sources_cases import (
    FILE_DISCOVERY_TEST_CASES,
)

# Context IDs for fixture parameterization
MOCK_CONTEXT = 1
INTEGRATION_CONTEXT = 2


@pytest.fixture(
    params=[
        pytest.param(MOCK_CONTEXT, id="mock", marks=pytest.mark.mock),
        pytest.param(
            INTEGRATION_CONTEXT,
            id="integration",
            marks=pytest.mark.integration,
        ),
    ],
)
def context(request: pytest.FixtureRequest) -> Any:  # type: ignore[no-any-return]
    # Return type is Any due to pytest param mechanics; see ONEX test standards
    return request.param


@pytest.fixture(
    params=[
        pytest.param("filesystem", id="filesystem"),
        pytest.param("tree", id="tree"),
        pytest.param("hybrid_warn", id="hybrid_warn"),
        pytest.param("hybrid_strict", id="hybrid_strict"),
    ],
)
def discovery_source(request: pytest.FixtureRequest) -> Any:
    if request.param == "filesystem":
        return DirectoryTraverser()
    if request.param == "tree":
        return TreeFileDiscoverySource()
    if request.param == "hybrid_warn":
        return HybridFileDiscoverySource(strict_mode=False)
    if request.param == "hybrid_strict":
        return HybridFileDiscoverySource(strict_mode=True)
    msg = f"Unknown discovery source: {request.param}"
    raise OnexError(
        msg,
        CoreErrorCode.INVALID_PARAMETER,
    )


@pytest.mark.parametrize(("case_name", "case_cls"), FILE_DISCOVERY_TEST_CASES.items())
def test_file_discovery_sources(
    case_name: str,
    case_cls: type,
    discovery_source: Any,
    tmp_path: Path,
    context: int,
    request: pytest.FixtureRequest,
) -> None:
    """
    Protocol-first, registry-driven test for file discovery sources.
    All dependencies are injected via fixtures. No test markers for categorization.
    """
    # Setup test case
    case = case_cls()
    # Determine the discovery source type string
    source_type = (
        request.fixturenames[1]
        if hasattr(request, "fixturenames") and len(request.fixturenames) > 1
        else None
    )
    # Fallback: try to infer from class name
    if hasattr(discovery_source, "__class__"):
        class_name = discovery_source.__class__.__name__.lower()
        if "filesystem" in class_name:
            source_type = "filesystem"
        elif "tree" in class_name:
            source_type = "tree"
        elif "hybrid" in class_name:
            if getattr(discovery_source, "strict_mode", False):
                source_type = "hybrid_strict"
            else:
                source_type = "hybrid_warn"
    # Skip if not supported
    if source_type not in getattr(case, "supported_sources", []):
        pytest.skip(
            f"Test case {case_name} does not support discovery source {source_type}",
        )
    test_dir = case.setup(tmp_path)
    # Run the test case with the injected discovery source
    case.run(discovery_source, test_dir)


# Remove count_files if not used or if it causes type issues
