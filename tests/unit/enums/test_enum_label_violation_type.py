"""Unit tests for EnumLabelViolationType."""

from __future__ import annotations

from omnibase_core.enums.enum_label_violation_type import EnumLabelViolationType


class TestEnumLabelViolationType:
    """Tests for EnumLabelViolationType enum."""

    def test_all_values_exist(self) -> None:
        """Test all expected enum values exist."""
        assert EnumLabelViolationType.FORBIDDEN_KEY.value == "forbidden_key"
        assert EnumLabelViolationType.KEY_NOT_ALLOWED.value == "key_not_allowed"
        assert EnumLabelViolationType.VALUE_TOO_LONG.value == "value_too_long"

    def test_str_representation(self) -> None:
        """Test string representation returns value."""
        assert str(EnumLabelViolationType.FORBIDDEN_KEY) == "forbidden_key"
        assert str(EnumLabelViolationType.KEY_NOT_ALLOWED) == "key_not_allowed"
        assert str(EnumLabelViolationType.VALUE_TOO_LONG) == "value_too_long"

    def test_enum_count(self) -> None:
        """Test enum has exactly 3 values."""
        assert len(EnumLabelViolationType) == 3

    def test_enum_is_str_subclass(self) -> None:
        """Test enum is a string subclass for serialization."""
        assert isinstance(EnumLabelViolationType.FORBIDDEN_KEY, str)
