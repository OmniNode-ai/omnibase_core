# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for EnumAcknowledgmentType enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_acknowledgment_type import EnumAcknowledgmentType


@pytest.mark.unit
class TestEnumAcknowledgmentType:
    """Test cases for EnumAcknowledgmentType enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumAcknowledgmentType.BOOTSTRAP_ACK == "bootstrap_ack"
        assert EnumAcknowledgmentType.DISCOVERY_ACK == "discovery_ack"
        assert EnumAcknowledgmentType.REGISTRATION_ACK == "registration_ack"
        assert EnumAcknowledgmentType.HEALTH_CHECK_ACK == "health_check_ack"
        assert EnumAcknowledgmentType.SHUTDOWN_ACK == "shutdown_ack"
        assert EnumAcknowledgmentType.UPDATE_ACK == "update_ack"
        assert EnumAcknowledgmentType.ERROR_ACK == "error_ack"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumAcknowledgmentType, str)
        assert issubclass(EnumAcknowledgmentType, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        ack_type = EnumAcknowledgmentType.BOOTSTRAP_ACK
        assert isinstance(ack_type, str)
        assert ack_type == "bootstrap_ack"
        assert len(ack_type) == 13
        assert ack_type.startswith("bootstrap")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumAcknowledgmentType)
        assert len(values) == 7
        assert EnumAcknowledgmentType.BOOTSTRAP_ACK in values
        assert EnumAcknowledgmentType.ERROR_ACK in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "bootstrap_ack" in EnumAcknowledgmentType
        assert "invalid_ack" not in EnumAcknowledgmentType

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        ack1 = EnumAcknowledgmentType.BOOTSTRAP_ACK
        ack2 = EnumAcknowledgmentType.DISCOVERY_ACK

        assert ack1 != ack2
        assert ack1 == "bootstrap_ack"
        assert ack2 == "discovery_ack"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        ack_type = EnumAcknowledgmentType.HEALTH_CHECK_ACK
        serialized = ack_type.value
        assert serialized == "health_check_ack"

        # Test JSON serialization
        import json

        json_str = json.dumps(ack_type)
        assert json_str == '"health_check_ack"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        ack_type = EnumAcknowledgmentType("registration_ack")
        assert ack_type == EnumAcknowledgmentType.REGISTRATION_ACK

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumAcknowledgmentType("invalid_ack")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "bootstrap_ack",
            "discovery_ack",
            "registration_ack",
            "health_check_ack",
            "shutdown_ack",
            "update_ack",
            "error_ack",
        }

        actual_values = {member.value for member in EnumAcknowledgmentType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Canonical acknowledgment types for ONEX discovery"
            in EnumAcknowledgmentType.__doc__
        )
