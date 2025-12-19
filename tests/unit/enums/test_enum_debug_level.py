"""
Unit tests for EnumDebugLevel.

Tests all aspects of the debug level enum including:
- Enum value validation
- Verbosity and severity ordering
- Level comparison methods
- String representation
- JSON serialization compatibility
- Pydantic integration
- Debug level inclusion logic
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_debug_level import EnumDebugLevel


@pytest.mark.unit
class TestEnumDebugLevel:
    """Test cases for EnumDebugLevel."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "DEBUG": "debug",
            "INFO": "info",
            "WARN": "warn",
            "ERROR": "error",
        }

        for name, value in expected_values.items():
            debug_level = getattr(EnumDebugLevel, name)
            assert debug_level.value == value
            assert str(debug_level) == value  # Has __str__ method

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(EnumDebugLevel.DEBUG) == "debug"
        assert str(EnumDebugLevel.INFO) == "info"
        assert str(EnumDebugLevel.WARN) == "warn"
        assert str(EnumDebugLevel.ERROR) == "error"

    def test_get_verbosity_order(self):
        """Test the get_verbosity_order class method."""
        verbosity_order = EnumDebugLevel.get_verbosity_order()
        expected_order = [
            EnumDebugLevel.ERROR,
            EnumDebugLevel.WARN,
            EnumDebugLevel.INFO,
            EnumDebugLevel.DEBUG,
        ]

        assert verbosity_order == expected_order
        assert len(verbosity_order) == 4

        # Verify order is from least to most verbose
        assert verbosity_order[0] == EnumDebugLevel.ERROR  # Least verbose
        assert verbosity_order[-1] == EnumDebugLevel.DEBUG  # Most verbose

    def test_get_severity_order(self):
        """Test the get_severity_order class method."""
        severity_order = EnumDebugLevel.get_severity_order()
        expected_order = [
            EnumDebugLevel.ERROR,
            EnumDebugLevel.WARN,
            EnumDebugLevel.INFO,
            EnumDebugLevel.DEBUG,
        ]

        assert severity_order == expected_order
        assert len(severity_order) == 4

        # Verify order is from most to least severe
        assert severity_order[0] == EnumDebugLevel.ERROR  # Most severe
        assert severity_order[-1] == EnumDebugLevel.DEBUG  # Least severe

    def test_is_more_verbose_than(self):
        """Test the is_more_verbose_than method."""
        # DEBUG is most verbose
        assert EnumDebugLevel.DEBUG.is_more_verbose_than(EnumDebugLevel.INFO) is True
        assert EnumDebugLevel.DEBUG.is_more_verbose_than(EnumDebugLevel.WARN) is True
        assert EnumDebugLevel.DEBUG.is_more_verbose_than(EnumDebugLevel.ERROR) is True

        # INFO is more verbose than WARN and ERROR
        assert EnumDebugLevel.INFO.is_more_verbose_than(EnumDebugLevel.WARN) is True
        assert EnumDebugLevel.INFO.is_more_verbose_than(EnumDebugLevel.ERROR) is True
        assert EnumDebugLevel.INFO.is_more_verbose_than(EnumDebugLevel.DEBUG) is False

        # WARN is more verbose than ERROR
        assert EnumDebugLevel.WARN.is_more_verbose_than(EnumDebugLevel.ERROR) is True
        assert EnumDebugLevel.WARN.is_more_verbose_than(EnumDebugLevel.INFO) is False
        assert EnumDebugLevel.WARN.is_more_verbose_than(EnumDebugLevel.DEBUG) is False

        # ERROR is least verbose
        assert EnumDebugLevel.ERROR.is_more_verbose_than(EnumDebugLevel.WARN) is False
        assert EnumDebugLevel.ERROR.is_more_verbose_than(EnumDebugLevel.INFO) is False
        assert EnumDebugLevel.ERROR.is_more_verbose_than(EnumDebugLevel.DEBUG) is False

        # Same level is not more verbose
        assert EnumDebugLevel.INFO.is_more_verbose_than(EnumDebugLevel.INFO) is False

    def test_includes_level(self):
        """Test the includes_level method."""
        # DEBUG includes all levels
        assert EnumDebugLevel.DEBUG.includes_level(EnumDebugLevel.DEBUG) is True
        assert EnumDebugLevel.DEBUG.includes_level(EnumDebugLevel.INFO) is True
        assert EnumDebugLevel.DEBUG.includes_level(EnumDebugLevel.WARN) is True
        assert EnumDebugLevel.DEBUG.includes_level(EnumDebugLevel.ERROR) is True

        # INFO includes INFO, WARN, ERROR
        assert EnumDebugLevel.INFO.includes_level(EnumDebugLevel.DEBUG) is False
        assert EnumDebugLevel.INFO.includes_level(EnumDebugLevel.INFO) is True
        assert EnumDebugLevel.INFO.includes_level(EnumDebugLevel.WARN) is True
        assert EnumDebugLevel.INFO.includes_level(EnumDebugLevel.ERROR) is True

        # WARN includes WARN, ERROR
        assert EnumDebugLevel.WARN.includes_level(EnumDebugLevel.DEBUG) is False
        assert EnumDebugLevel.WARN.includes_level(EnumDebugLevel.INFO) is False
        assert EnumDebugLevel.WARN.includes_level(EnumDebugLevel.WARN) is True
        assert EnumDebugLevel.WARN.includes_level(EnumDebugLevel.ERROR) is True

        # ERROR includes only ERROR
        assert EnumDebugLevel.ERROR.includes_level(EnumDebugLevel.DEBUG) is False
        assert EnumDebugLevel.ERROR.includes_level(EnumDebugLevel.INFO) is False
        assert EnumDebugLevel.ERROR.includes_level(EnumDebugLevel.WARN) is False
        assert EnumDebugLevel.ERROR.includes_level(EnumDebugLevel.ERROR) is True

    def test_verbosity_ordering_consistency(self):
        """Test that verbosity and severity orders are consistent."""
        verbosity_order = EnumDebugLevel.get_verbosity_order()
        severity_order = EnumDebugLevel.get_severity_order()

        # They should be the same (severity decreases as verbosity increases)
        assert verbosity_order == severity_order

        # Test transitivity of verbosity
        for i in range(len(verbosity_order)):
            for j in range(i + 1, len(verbosity_order)):
                less_verbose = verbosity_order[i]
                more_verbose = verbosity_order[j]
                assert more_verbose.is_more_verbose_than(less_verbose) is True
                assert less_verbose.is_more_verbose_than(more_verbose) is False

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumDebugLevel.DEBUG == EnumDebugLevel.DEBUG
        assert EnumDebugLevel.INFO != EnumDebugLevel.WARN
        assert EnumDebugLevel.ERROR == EnumDebugLevel.ERROR

    def test_enum_membership(self):
        """Test enum membership checking."""
        all_debug_levels = [
            EnumDebugLevel.DEBUG,
            EnumDebugLevel.INFO,
            EnumDebugLevel.WARN,
            EnumDebugLevel.ERROR,
        ]

        for level in all_debug_levels:
            assert level in EnumDebugLevel

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        debug_levels = list(EnumDebugLevel)
        assert len(debug_levels) == 4

        level_values = [level.value for level in debug_levels]
        expected_values = ["debug", "info", "warn", "error"]

        assert set(level_values) == set(expected_values)

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Test direct serialization
        level = EnumDebugLevel.DEBUG
        json_str = json.dumps(level, default=str)
        assert json_str == '"debug"'

        # Test in dictionary
        data = {"debug_level": EnumDebugLevel.INFO}
        json_str = json.dumps(data, default=str)
        assert '"debug_level": "info"' in json_str

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class EnumDebugConfig(BaseModel):
            level: EnumDebugLevel

        # Test valid enum assignment
        config = EnumDebugConfig(level=EnumDebugLevel.WARN)
        assert config.level == EnumDebugLevel.WARN

        # Test string assignment (should work due to str inheritance)
        config = EnumDebugConfig(level="error")
        assert config.level == EnumDebugLevel.ERROR

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            EnumDebugConfig(level="invalid_level")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class EnumDebugConfig(BaseModel):
            level: EnumDebugLevel

        config = EnumDebugConfig(level=EnumDebugLevel.DEBUG)

        # Test dict serialization
        config_dict = config.model_dump()
        assert config_dict == {"level": "debug"}

        # Test JSON serialization
        json_str = config.model_dump_json()
        assert json_str == '{"level":"debug"}'

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Test case sensitivity
        assert EnumDebugLevel.DEBUG.value == "debug"
        assert EnumDebugLevel.DEBUG.value != "DEBUG"

        # Test that we can't create invalid enum values
        with pytest.raises((ValueError, AttributeError)):
            _ = EnumDebugLevel("invalid_level")

    def test_comprehensive_debug_scenarios(self):
        """Test comprehensive debugging scenarios."""
        # Test production logging (ERROR only)
        error_level = EnumDebugLevel.ERROR
        assert error_level.includes_level(EnumDebugLevel.ERROR) is True
        assert error_level.includes_level(EnumDebugLevel.WARN) is False
        assert error_level.includes_level(EnumDebugLevel.INFO) is False
        assert error_level.includes_level(EnumDebugLevel.DEBUG) is False

        # Test development debugging (DEBUG all)
        debug_level = EnumDebugLevel.DEBUG
        assert debug_level.includes_level(EnumDebugLevel.ERROR) is True
        assert debug_level.includes_level(EnumDebugLevel.WARN) is True
        assert debug_level.includes_level(EnumDebugLevel.INFO) is True
        assert debug_level.includes_level(EnumDebugLevel.DEBUG) is True

        # Test staging environment (INFO and above)
        info_level = EnumDebugLevel.INFO
        assert info_level.includes_level(EnumDebugLevel.ERROR) is True
        assert info_level.includes_level(EnumDebugLevel.WARN) is True
        assert info_level.includes_level(EnumDebugLevel.INFO) is True
        assert info_level.includes_level(EnumDebugLevel.DEBUG) is False

    def test_level_inclusion_transitivity(self):
        """Test that level inclusion is transitive."""
        levels = EnumDebugLevel.get_verbosity_order()

        # For each level, it should include all less verbose levels
        for i, current_level in enumerate(levels):
            for j, other_level in enumerate(levels):
                if j <= i:  # Less or equally verbose
                    assert current_level.includes_level(other_level) is True
                else:  # More verbose
                    assert current_level.includes_level(other_level) is False

    def test_yaml_serialization_compatibility(self):
        """Test YAML serialization compatibility."""
        import yaml

        # Test that enum values are YAML serializable
        data = {"log_level": EnumDebugLevel.WARN.value}
        yaml_str = yaml.dump(data, default_flow_style=False)
        assert "log_level: warn" in yaml_str

        # Test that we can load it back
        loaded_data = yaml.safe_load(yaml_str)
        assert loaded_data["log_level"] == "warn"

        # Test that the enum value equals the string
        assert EnumDebugLevel.WARN == "warn"

    def test_logging_level_mapping(self):
        """Test compatibility with standard logging levels."""
        # These enum values should be compatible with common logging systems
        logging_mapping = {
            EnumDebugLevel.DEBUG: "debug",
            EnumDebugLevel.INFO: "info",
            EnumDebugLevel.WARN: "warn",  # or "warning"
            EnumDebugLevel.ERROR: "error",
        }

        for enum_level, expected_log_level in logging_mapping.items():
            assert enum_level.value == expected_log_level


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
