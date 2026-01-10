# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for EnumDashboardStatus."""

from enum import Enum

import pytest

from omnibase_core.enums.enum_dashboard_status import EnumDashboardStatus


@pytest.mark.unit
class TestEnumDashboardStatus:
    """Tests for EnumDashboardStatus enum."""

    def test_all_values_exist(self) -> None:
        """Test that all expected status values exist."""
        assert EnumDashboardStatus.INITIALIZING == "initializing"
        assert EnumDashboardStatus.CONNECTED == "connected"
        assert EnumDashboardStatus.DISCONNECTED == "disconnected"
        assert EnumDashboardStatus.ERROR == "error"

    def test_value_count(self) -> None:
        """Test expected number of status values."""
        assert len(EnumDashboardStatus) == 4

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumDashboardStatus, str)
        assert issubclass(EnumDashboardStatus, Enum)

    def test_is_operational_property(self) -> None:
        """Test is_operational property."""
        assert EnumDashboardStatus.CONNECTED.is_operational is True
        assert EnumDashboardStatus.INITIALIZING.is_operational is False
        assert EnumDashboardStatus.DISCONNECTED.is_operational is False
        assert EnumDashboardStatus.ERROR.is_operational is False

    def test_is_terminal_property(self) -> None:
        """Test is_terminal property."""
        assert EnumDashboardStatus.ERROR.is_terminal is True
        assert EnumDashboardStatus.CONNECTED.is_terminal is False
        assert EnumDashboardStatus.DISCONNECTED.is_terminal is False
        assert EnumDashboardStatus.INITIALIZING.is_terminal is False

    def test_requires_reconnection_property(self) -> None:
        """Test requires_reconnection property."""
        assert EnumDashboardStatus.DISCONNECTED.requires_reconnection is True
        assert EnumDashboardStatus.ERROR.requires_reconnection is True
        assert EnumDashboardStatus.CONNECTED.requires_reconnection is False
        assert EnumDashboardStatus.INITIALIZING.requires_reconnection is False

    def test_operational_does_not_require_reconnection(self) -> None:
        """Test that operational status does not require reconnection."""
        for status in EnumDashboardStatus:
            if status.is_operational:
                assert status.requires_reconnection is False

    def test_terminal_requires_reconnection(self) -> None:
        """Test that terminal status requires reconnection."""
        for status in EnumDashboardStatus:
            if status.is_terminal:
                assert status.requires_reconnection is True

    def test_string_conversion(self) -> None:
        """Test string conversion and str enum behavior."""
        # str(enum) returns full representation
        assert "INITIALIZING" in str(EnumDashboardStatus.INITIALIZING)
        # But as str subclass, equality with string works
        assert EnumDashboardStatus.INITIALIZING == "initializing"
        assert EnumDashboardStatus.CONNECTED == "connected"
        assert EnumDashboardStatus.DISCONNECTED == "disconnected"
        assert EnumDashboardStatus.ERROR == "error"

    def test_value_attribute(self) -> None:
        """Test value attribute."""
        assert EnumDashboardStatus.INITIALIZING.value == "initializing"
        assert EnumDashboardStatus.CONNECTED.value == "connected"
        assert EnumDashboardStatus.DISCONNECTED.value == "disconnected"
        assert EnumDashboardStatus.ERROR.value == "error"

    def test_from_string(self) -> None:
        """Test enum creation from string value."""
        assert EnumDashboardStatus("initializing") == EnumDashboardStatus.INITIALIZING
        assert EnumDashboardStatus("connected") == EnumDashboardStatus.CONNECTED
        assert EnumDashboardStatus("disconnected") == EnumDashboardStatus.DISCONNECTED
        assert EnumDashboardStatus("error") == EnumDashboardStatus.ERROR

    def test_invalid_value_raises(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumDashboardStatus("invalid")

        with pytest.raises(ValueError):
            EnumDashboardStatus("")

    def test_enum_iteration(self) -> None:
        """Test that we can iterate over enum values."""
        values = list(EnumDashboardStatus)
        assert len(values) == 4
        assert EnumDashboardStatus.INITIALIZING in values
        assert EnumDashboardStatus.CONNECTED in values
        assert EnumDashboardStatus.DISCONNECTED in values
        assert EnumDashboardStatus.ERROR in values

    def test_enum_membership(self) -> None:
        """Test membership testing."""
        assert EnumDashboardStatus.CONNECTED in EnumDashboardStatus
        assert "connected" in EnumDashboardStatus
        assert "invalid_status" not in EnumDashboardStatus

    def test_enum_comparison(self) -> None:
        """Test enum comparison."""
        assert EnumDashboardStatus.CONNECTED == EnumDashboardStatus.CONNECTED
        assert EnumDashboardStatus.CONNECTED != EnumDashboardStatus.ERROR
        assert EnumDashboardStatus.CONNECTED == "connected"

    def test_all_expected_values(self) -> None:
        """Test that all expected values are present."""
        expected_values = {"initializing", "connected", "disconnected", "error"}
        actual_values = {member.value for member in EnumDashboardStatus}
        assert actual_values == expected_values

    def test_enum_docstring(self) -> None:
        """Test that enum has proper docstring."""
        assert EnumDashboardStatus.__doc__ is not None
        assert "dashboard" in EnumDashboardStatus.__doc__.lower()

    def test_json_roundtrip(self) -> None:
        """Test JSON serialization roundtrip."""
        import json

        for status in EnumDashboardStatus:
            # Serialize to JSON
            json_str = json.dumps(status.value)
            # Deserialize from JSON
            deserialized = json.loads(json_str)
            # Reconstruct enum
            reconstructed = EnumDashboardStatus(deserialized)
            assert reconstructed == status
