"""Unit tests for EnumMetricsPolicyViolationAction."""

from omnibase_core.enums.enum_metrics_policy_violation_action import (
    EnumMetricsPolicyViolationAction,
)


class TestEnumMetricsPolicyViolationAction:
    """Tests for EnumMetricsPolicyViolationAction enum."""

    def test_all_values_exist(self) -> None:
        """Test all expected enum values exist."""
        assert EnumMetricsPolicyViolationAction.RAISE.value == "raise"
        assert EnumMetricsPolicyViolationAction.WARN_AND_DROP.value == "warn_and_drop"
        assert EnumMetricsPolicyViolationAction.DROP_SILENT.value == "drop_silent"
        assert EnumMetricsPolicyViolationAction.WARN_AND_STRIP.value == "warn_and_strip"

    def test_str_representation(self) -> None:
        """Test string representation returns value."""
        assert str(EnumMetricsPolicyViolationAction.RAISE) == "raise"
        assert str(EnumMetricsPolicyViolationAction.WARN_AND_DROP) == "warn_and_drop"

    def test_enum_count(self) -> None:
        """Test enum has exactly 4 values."""
        assert len(EnumMetricsPolicyViolationAction) == 4

    def test_enum_is_str_subclass(self) -> None:
        """Test enum is a string subclass for serialization."""
        assert isinstance(EnumMetricsPolicyViolationAction.RAISE, str)
