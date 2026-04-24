# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumModelRoutingBackend (OMN-9623)."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_model_routing_backend import EnumModelRoutingBackend


@pytest.mark.unit
class TestEnumModelRoutingBackend:
    """Test cases for EnumModelRoutingBackend enum."""

    def test_enum_values(self) -> None:
        """Test that enum has expected SCREAMING_SNAKE string values."""
        assert EnumModelRoutingBackend.BIFROST.value == "BIFROST"
        assert EnumModelRoutingBackend.DIRECT.value == "DIRECT"
        assert EnumModelRoutingBackend.OPENAI_COMPAT.value == "OPENAI_COMPAT"

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumModelRoutingBackend, str)
        assert issubclass(EnumModelRoutingBackend, Enum)

    def test_enum_string_behavior(self) -> None:
        """Test that enum values behave as strings."""
        backend = EnumModelRoutingBackend.BIFROST
        assert isinstance(backend, str)
        assert str(backend) == "BIFROST"

    def test_enum_iteration(self) -> None:
        """Test that enum can be iterated and has exactly 3 members."""
        values = list(EnumModelRoutingBackend)
        assert len(values) == 3

    def test_enum_all_values(self) -> None:
        """Test that all expected values are present and no extras."""
        expected = {"BIFROST", "DIRECT", "OPENAI_COMPAT"}
        actual = {member.value for member in EnumModelRoutingBackend}
        assert actual == expected

    def test_enum_membership(self) -> None:
        """Test enum membership via string values."""
        values = {m.value for m in EnumModelRoutingBackend}
        assert "BIFROST" in values
        assert "DIRECT" in values
        assert "OPENAI_COMPAT" in values
        assert "invalid_backend" not in values

    def test_enum_unique(self) -> None:
        """Test that all enum values are unique (enforced by @unique)."""
        values = [m.value for m in EnumModelRoutingBackend]
        assert len(values) == len(set(values))

    def test_enum_serialization(self) -> None:
        """Test that enum values serialize to their string representations."""
        backend = EnumModelRoutingBackend.OPENAI_COMPAT
        assert json.dumps(backend) == '"OPENAI_COMPAT"'

    def test_enum_deserialization(self) -> None:
        """Test that enum members can be constructed from their string values."""
        assert EnumModelRoutingBackend("BIFROST") == EnumModelRoutingBackend.BIFROST
        assert EnumModelRoutingBackend("DIRECT") == EnumModelRoutingBackend.DIRECT

    def test_enum_invalid_value_raises(self) -> None:
        """Test that constructing from an invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumModelRoutingBackend("invalid")
