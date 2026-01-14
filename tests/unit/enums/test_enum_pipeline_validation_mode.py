"""Unit tests for EnumPipelineValidationMode."""

from enum import Enum

import pytest

from omnibase_core.enums.enum_pipeline_validation_mode import EnumPipelineValidationMode


@pytest.mark.unit
class TestEnumPipelineValidationMode:
    """Test suite for EnumPipelineValidationMode enumeration."""

    def test_string_returns_value(self) -> None:
        """Test that str() returns the .value (StrValueHelper behavior)."""
        assert str(EnumPipelineValidationMode.STRICT) == "strict"
        assert str(EnumPipelineValidationMode.LENIENT) == "lenient"
        assert str(EnumPipelineValidationMode.SMOKE) == "smoke"
        assert str(EnumPipelineValidationMode.REGRESSION) == "regression"
        assert str(EnumPipelineValidationMode.INTEGRATION) == "integration"

    def test_value_property(self) -> None:
        """Test that .value returns the correct string."""
        assert EnumPipelineValidationMode.STRICT.value == "strict"
        assert EnumPipelineValidationMode.LENIENT.value == "lenient"
        assert EnumPipelineValidationMode.SMOKE.value == "smoke"
        assert EnumPipelineValidationMode.REGRESSION.value == "regression"
        assert EnumPipelineValidationMode.INTEGRATION.value == "integration"

    def test_all_members_exist(self) -> None:
        """Test that all expected enum members exist."""
        values = [m.value for m in EnumPipelineValidationMode]
        assert "strict" in values
        assert "lenient" in values
        assert "smoke" in values
        assert "regression" in values
        assert "integration" in values

    def test_unique_values(self) -> None:
        """Test that all enum values are unique."""
        values = [m.value for m in EnumPipelineValidationMode]
        assert len(values) == len(set(values))

    def test_enum_count(self) -> None:
        """Test that enum has exactly 5 members."""
        members = list(EnumPipelineValidationMode)
        assert len(members) == 5

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumPipelineValidationMode, str)
        assert issubclass(EnumPipelineValidationMode, Enum)

    def test_enum_string_equality(self) -> None:
        """Test that enum members equal their string values."""
        assert EnumPipelineValidationMode.STRICT == "strict"
        assert EnumPipelineValidationMode.LENIENT == "lenient"
        assert EnumPipelineValidationMode.SMOKE == "smoke"
        assert EnumPipelineValidationMode.REGRESSION == "regression"
        assert EnumPipelineValidationMode.INTEGRATION == "integration"

    def test_enum_comparison(self) -> None:
        """Test enum member equality."""
        mode1 = EnumPipelineValidationMode.STRICT
        mode2 = EnumPipelineValidationMode.STRICT
        mode3 = EnumPipelineValidationMode.LENIENT

        assert mode1 == mode2
        assert mode1 != mode3
        assert mode1 is mode2

    def test_enum_membership(self) -> None:
        """Test membership testing."""
        assert EnumPipelineValidationMode.STRICT in EnumPipelineValidationMode
        assert "strict" in EnumPipelineValidationMode
        assert "invalid_mode" not in EnumPipelineValidationMode

    def test_enum_deserialization(self) -> None:
        """Test enum deserialization from string."""
        assert EnumPipelineValidationMode("strict") == EnumPipelineValidationMode.STRICT
        assert EnumPipelineValidationMode("smoke") == EnumPipelineValidationMode.SMOKE

    def test_enum_invalid_values(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumPipelineValidationMode("invalid_mode")

        with pytest.raises(ValueError):
            EnumPipelineValidationMode("")
