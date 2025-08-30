# === OmniNode:Metadata ===
# metadata_version: 0.1.0
# protocol_version: 0.1.0
# owner: OmniNode Team
# copyright: OmniNode Team
# schema_version: 0.1.0
# name: test_utils_uri_parser.py
# version: 1.0.0
# uuid: 20ed1ef4-d3c8-4054-ba2e-1d34d81fc116
# author: OmniNode Team
# created_at: 2025-05-21T12:41:40.173018
# last_modified_at: 2025-05-21T16:42:46.082019
# description: Stamped by ToolPython
# state_contract: state_contract://default
# lifecycle: active
# hash: 1b7e2e40ddc8e8931a8130274b9d115d2345b318d84255a222fedac5253bdcc0
# entrypoint: python@test_utils_uri_parser.py
# runtime_language_hint: python>=3.11
# namespace: onex.stamped.test_utils_uri_parser
# meta_type: tool
# === /OmniNode:Metadata ===


"""
Standards-Compliant Test File for ONEX/OmniBase URI Parser

This file follows the canonical test pattern as demonstrated in src/omnibase/utils/tests/test_node_metadata_extractor.py. It demonstrates:
- Naming conventions: test_ prefix, lowercase, descriptive
- Context-agnostic, registry-driven, fixture-injected testing
- Use of both mock (unit) and integration (real) contexts via pytest fixture parametrization
- No global state; all dependencies are injected
- Registry-driven test case execution pattern
- Compliance with all standards in docs/standards.md and docs/testing.md

All new URI parser tests should follow this pattern unless a justified exception is documented and reviewed.
"""

from typing import Any

import pytest

from omnibase_core.utils.utils_tests.utils_test_uri_parser_cases import \
    URI_PARSER_TEST_CASES
from omnibase_core.utils.utils_uri_parser import CanonicalUriParser


@pytest.fixture(
    params=[
        pytest.param("mock", id="mock", marks=pytest.mark.mock),
        pytest.param("integration", id="integration", marks=pytest.mark.integration),
    ]
)
def context(request: pytest.FixtureRequest) -> Any:  # type: ignore[no-any-return]
    # Return type is Any due to pytest param mechanics; see ONEX test standards
    return request.param


@pytest.mark.parametrize(
    "context", ["mock", "integration"], ids=["mock", "integration"]
)
@pytest.mark.parametrize(
    "test_case",
    list(URI_PARSER_TEST_CASES.values()),
    ids=list(URI_PARSER_TEST_CASES.keys()),
)
def test_utils_uri_parser_cases(test_case: type, context: str) -> None:
    """Test URI parser cases for both mock and integration contexts."""
    parser = CanonicalUriParser()
    test_case().run(parser, context)


# TODO: Protocol-based extension and negative/edge cases in M1+


def get_uri_type(uri: str) -> str:
    """Return the type of the given URI as a string (stub for standards compliance)."""
    return "mock_type"


# Remove parse_uri if not used or if it causes type issues
