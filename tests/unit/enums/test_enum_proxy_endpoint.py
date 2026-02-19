# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumProxyEndpoint."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_proxy_endpoint import EnumProxyEndpoint


@pytest.mark.unit
class TestEnumProxyEndpoint:
    """Test suite for EnumProxyEndpoint."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumProxyEndpoint.V1_MESSAGES == "v1/messages"
        assert EnumProxyEndpoint.V1_COMPLETE == "v1/complete"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumProxyEndpoint, str)
        assert issubclass(EnumProxyEndpoint, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        endpoint = EnumProxyEndpoint.V1_MESSAGES
        assert isinstance(endpoint, str)
        assert endpoint == "v1/messages"
        assert len(endpoint) == 11

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumProxyEndpoint)
        assert len(values) == 2
        assert EnumProxyEndpoint.V1_MESSAGES in values
        assert EnumProxyEndpoint.V1_COMPLETE in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumProxyEndpoint.V1_COMPLETE in EnumProxyEndpoint
        assert "v1/complete" in [e.value for e in EnumProxyEndpoint]

    def test_enum_comparison(self):
        """Test enum comparison."""
        endpoint1 = EnumProxyEndpoint.V1_MESSAGES
        endpoint2 = EnumProxyEndpoint.V1_MESSAGES
        endpoint3 = EnumProxyEndpoint.V1_COMPLETE

        assert endpoint1 == endpoint2
        assert endpoint1 != endpoint3
        assert endpoint1 == "v1/messages"

    def test_enum_serialization(self):
        """Test enum serialization."""
        endpoint = EnumProxyEndpoint.V1_COMPLETE
        serialized = endpoint.value
        assert serialized == "v1/complete"
        json_str = json.dumps(endpoint)
        assert json_str == '"v1/complete"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        endpoint = EnumProxyEndpoint("v1/messages")
        assert endpoint == EnumProxyEndpoint.V1_MESSAGES

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumProxyEndpoint("invalid/endpoint")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"v1/messages", "v1/complete"}
        actual_values = {e.value for e in EnumProxyEndpoint}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumProxyEndpoint.__doc__ is not None
        assert "endpoint" in EnumProxyEndpoint.__doc__.lower()

    def test_endpoint_versioning(self):
        """Test that all endpoints follow versioning pattern."""
        for endpoint in EnumProxyEndpoint:
            # All should start with v1/
            assert endpoint.value.startswith("v1/")

    def test_endpoint_api_types(self):
        """Test different API endpoint types."""
        # Messages API
        messages_api = {EnumProxyEndpoint.V1_MESSAGES}
        # Completion API
        completion_api = {EnumProxyEndpoint.V1_COMPLETE}

        assert all(e in EnumProxyEndpoint for e in messages_api)
        assert all(e in EnumProxyEndpoint for e in completion_api)
