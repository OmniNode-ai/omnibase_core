"""Unit tests for EnumDeregistrationReason and is_planned_deregistration.

Test coverage for deregistration reason enumeration, the is_planned() method,
and the standalone is_planned_deregistration() function that handles both
enum values and arbitrary strings.
"""

import pytest

from omnibase_core.enums import EnumDeregistrationReason, is_planned_deregistration


@pytest.mark.unit
class TestEnumDeregistrationReason:
    """Test cases for EnumDeregistrationReason enum."""

    def test_enum_values(self) -> None:
        """Test all enum values are present."""
        expected_values = {"shutdown", "upgrade", "manual"}
        actual_values = {reason.value for reason in EnumDeregistrationReason}
        assert actual_values == expected_values

    def test_string_inheritance(self) -> None:
        """Test that enum inherits from str."""
        assert isinstance(EnumDeregistrationReason.SHUTDOWN, str)
        assert EnumDeregistrationReason.SHUTDOWN == "shutdown"
        assert EnumDeregistrationReason.UPGRADE == "upgrade"
        assert EnumDeregistrationReason.MANUAL == "manual"

    def test_str_representation(self) -> None:
        """Test string representation returns the value."""
        for reason in EnumDeregistrationReason:
            assert str(reason) == reason.value


@pytest.mark.unit
class TestEnumDeregistrationReasonIsPlanned:
    """Test cases for EnumDeregistrationReason.is_planned() method."""

    def test_is_planned_shutdown(self) -> None:
        """Test SHUTDOWN is considered planned."""
        assert EnumDeregistrationReason.SHUTDOWN.is_planned() is True

    def test_is_planned_upgrade(self) -> None:
        """Test UPGRADE is considered planned."""
        assert EnumDeregistrationReason.UPGRADE.is_planned() is True

    def test_is_planned_manual(self) -> None:
        """Test MANUAL is considered planned."""
        assert EnumDeregistrationReason.MANUAL.is_planned() is True

    def test_all_enum_values_are_planned(self) -> None:
        """Test all standard enum values are considered planned."""
        for reason in EnumDeregistrationReason:
            assert reason.is_planned() is True


@pytest.mark.unit
class TestIsPlannedDeregistrationFunction:
    """Test cases for the standalone is_planned_deregistration() function."""

    def test_with_enum_shutdown(self) -> None:
        """Test function with SHUTDOWN enum value."""
        assert is_planned_deregistration(EnumDeregistrationReason.SHUTDOWN) is True

    def test_with_enum_upgrade(self) -> None:
        """Test function with UPGRADE enum value."""
        assert is_planned_deregistration(EnumDeregistrationReason.UPGRADE) is True

    def test_with_enum_manual(self) -> None:
        """Test function with MANUAL enum value."""
        assert is_planned_deregistration(EnumDeregistrationReason.MANUAL) is True

    def test_with_string_shutdown(self) -> None:
        """Test function with 'shutdown' string returns True."""
        assert is_planned_deregistration("shutdown") is True

    def test_with_string_upgrade(self) -> None:
        """Test function with 'upgrade' string returns True."""
        assert is_planned_deregistration("upgrade") is True

    def test_with_string_manual(self) -> None:
        """Test function with 'manual' string returns True."""
        assert is_planned_deregistration("manual") is True

    def test_with_uppercase_string_shutdown(self) -> None:
        """Test function with 'SHUTDOWN' uppercase string returns True."""
        assert is_planned_deregistration("SHUTDOWN") is True

    def test_with_uppercase_string_upgrade(self) -> None:
        """Test function with 'UPGRADE' uppercase string returns True."""
        assert is_planned_deregistration("UPGRADE") is True

    def test_with_uppercase_string_manual(self) -> None:
        """Test function with 'MANUAL' uppercase string returns True."""
        assert is_planned_deregistration("MANUAL") is True

    def test_with_mixed_case_string(self) -> None:
        """Test function with mixed case strings returns True."""
        assert is_planned_deregistration("Shutdown") is True
        assert is_planned_deregistration("ShutDown") is True
        assert is_planned_deregistration("UpGrAdE") is True

    def test_with_custom_string_health_check_failure(self) -> None:
        """Test function with custom 'health_check_failure' string returns False."""
        assert is_planned_deregistration("health_check_failure") is False

    def test_with_custom_string_resource_exhaustion(self) -> None:
        """Test function with custom 'resource_exhaustion' string returns False."""
        assert is_planned_deregistration("resource_exhaustion") is False

    def test_with_custom_string_crash_recovery(self) -> None:
        """Test function with custom 'crash_recovery' string returns False."""
        assert is_planned_deregistration("crash_recovery") is False

    def test_with_custom_string_timeout(self) -> None:
        """Test function with custom 'timeout' string returns False."""
        assert is_planned_deregistration("timeout") is False

    def test_with_custom_string_unknown(self) -> None:
        """Test function with custom 'unknown' string returns False."""
        assert is_planned_deregistration("unknown") is False

    def test_with_empty_string(self) -> None:
        """Test function with empty string returns False."""
        assert is_planned_deregistration("") is False

    def test_with_whitespace_string(self) -> None:
        """Test function with whitespace-only string returns False."""
        assert is_planned_deregistration("   ") is False

    def test_backward_compatibility_enum_is_planned(self) -> None:
        """Test backward compatibility: enum is_planned() still works correctly."""
        # This test ensures the method on the enum still works after adding
        # the standalone function
        for reason in EnumDeregistrationReason:
            # Both the method and function should agree for enum values
            assert reason.is_planned() == is_planned_deregistration(reason)

    def test_function_handles_all_enum_members(self) -> None:
        """Test function correctly handles all enum members."""
        for reason in EnumDeregistrationReason:
            # All standard enum values should be planned
            assert is_planned_deregistration(reason) is True
            # String version should also work
            assert is_planned_deregistration(reason.value) is True
