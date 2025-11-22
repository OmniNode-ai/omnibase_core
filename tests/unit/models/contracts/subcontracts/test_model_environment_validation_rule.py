"""
Tests for ModelEnvironmentValidationRule.

Validates environment-specific validation rule configuration including
type safety, field constraints, and environment validation rule types.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_environment_validation_rule_type import (
    EnumEnvironmentValidationRuleType,
)
from omnibase_core.models.contracts.subcontracts.model_environment_validation_rule import (
    ModelEnvironmentValidationRule,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class TestModelEnvironmentValidationRuleValidation:
    """Test validation rules for environment validation rules."""

    def test_valid_rule_with_value_check_type(self) -> None:
        """Test that rules with value_check type are valid."""
        rule = ModelEnvironmentValidationRule(
            config_key="database_url",
            validation_rule="must_be_postgresql",
            rule_type=EnumEnvironmentValidationRuleType.VALUE_CHECK,
        )
        assert rule.config_key == "database_url"
        assert rule.rule_type == EnumEnvironmentValidationRuleType.VALUE_CHECK

    def test_valid_rule_with_format_type(self) -> None:
        """Test that rules with format type are valid."""
        rule = ModelEnvironmentValidationRule(
            config_key="api_key",
            validation_rule="must_match_pattern",
            rule_type=EnumEnvironmentValidationRuleType.FORMAT,
            format_pattern=r"^[A-Za-z0-9]{32}$",
        )
        assert rule.rule_type == EnumEnvironmentValidationRuleType.FORMAT
        assert rule.format_pattern is not None

    def test_valid_rule_with_range_type(self) -> None:
        """Test that rules with range type are valid."""
        rule = ModelEnvironmentValidationRule(
            config_key="port",
            validation_rule="must_be_in_range",
            rule_type=EnumEnvironmentValidationRuleType.RANGE,
            min_value=1024,
            max_value=65535,
        )
        assert rule.rule_type == EnumEnvironmentValidationRuleType.RANGE
        assert rule.min_value == 1024
        assert rule.max_value == 65535

    def test_valid_rule_with_allowed_values_type(self) -> None:
        """Test that rules with allowed_values type are valid."""
        rule = ModelEnvironmentValidationRule(
            config_key="log_level",
            validation_rule="must_be_in_list",
            rule_type=EnumEnvironmentValidationRuleType.ALLOWED_VALUES,
            allowed_values=["DEBUG", "INFO", "WARN", "ERROR"],
        )
        assert rule.rule_type == EnumEnvironmentValidationRuleType.ALLOWED_VALUES
        assert len(rule.allowed_values) == 4

    def test_valid_rule_with_all_optional_fields(self) -> None:
        """Test that rules with all optional fields are valid."""
        rule = ModelEnvironmentValidationRule(
            config_key="timeout",
            validation_rule="must_be_valid_timeout",
            rule_type=EnumEnvironmentValidationRuleType.RANGE,
            allowed_values=["fast", "medium", "slow"],
            min_value=1000,
            max_value=60000,
            format_pattern=r"^\d+$",
        )
        assert len(rule.allowed_values) == 3
        assert rule.min_value == 1000
        assert rule.max_value == 60000
        assert rule.format_pattern is not None

    def test_valid_rule_with_empty_allowed_values(self) -> None:
        """Test that rules with empty allowed_values list are valid."""
        rule = ModelEnvironmentValidationRule(
            config_key="field",
            validation_rule="check",
            allowed_values=[],
        )
        assert rule.allowed_values == []


class TestModelEnvironmentValidationRuleCreation:
    """Test creation and field constraints."""

    def test_required_fields(self) -> None:
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            ModelEnvironmentValidationRule()  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            ModelEnvironmentValidationRule(  # type: ignore[call-arg]  # Missing validation_rule
                config_key="field"
            )

        with pytest.raises(ValidationError):
            ModelEnvironmentValidationRule(  # type: ignore[call-arg]  # Missing config_key
                validation_rule="rule"
            )

    def test_default_values(self) -> None:
        """Test default field values."""
        rule = ModelEnvironmentValidationRule(
            config_key="test_key",
            validation_rule="test_rule",
        )
        assert rule.rule_type == EnumEnvironmentValidationRuleType.VALUE_CHECK
        assert rule.allowed_values == []
        assert rule.min_value is None
        assert rule.max_value is None
        assert rule.format_pattern is None

    def test_optional_fields(self) -> None:
        """Test optional field assignment."""
        rule = ModelEnvironmentValidationRule(
            config_key="test_key",
            validation_rule="test_rule",
            rule_type=EnumEnvironmentValidationRuleType.RANGE,
            allowed_values=["value1", "value2"],
            min_value=10,
            max_value=100,
            format_pattern=r"^\d+$",
        )
        assert rule.rule_type == EnumEnvironmentValidationRuleType.RANGE
        assert len(rule.allowed_values) == 2
        assert rule.min_value == 10
        assert rule.max_value == 100
        assert rule.format_pattern == r"^\d+$"

    def test_string_field_constraints(self) -> None:
        """Test string field minimum length constraints."""
        with pytest.raises(ValidationError):
            ModelEnvironmentValidationRule(
                config_key="",  # Empty string not allowed
                validation_rule="rule",
            )

        with pytest.raises(ValidationError):
            ModelEnvironmentValidationRule(
                config_key="key",
                validation_rule="",  # Empty string not allowed
            )

    def test_enum_values_for_rule_type(self) -> None:
        """Test that rule_type accepts all valid enum values with required fields."""
        from typing import Any

        # Map each rule_type to required fields
        rule_configs: dict[EnumEnvironmentValidationRuleType, dict[str, Any]] = {
            EnumEnvironmentValidationRuleType.VALUE_CHECK: {},
            EnumEnvironmentValidationRuleType.RANGE: {"min_value": 0},
            EnumEnvironmentValidationRuleType.FORMAT: {"format_pattern": r"^\d+$"},
            EnumEnvironmentValidationRuleType.ALLOWED_VALUES: {
                "allowed_values": ["value1"]
            },
        }

        for rule_type, extra_fields in rule_configs.items():
            rule = ModelEnvironmentValidationRule(
                config_key="test_key",
                validation_rule="test_rule",
                rule_type=rule_type,
                **extra_fields,  # type: ignore[arg-type]
            )
            assert rule.rule_type == rule_type


class TestModelEnvironmentValidationRuleEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_config_key_with_special_characters(self) -> None:
        """Test that config keys with special characters are valid."""
        special_keys = [
            "key_with_underscore",
            "key-with-dash",
            "key.with.dot",
            "key123",
            "KEY_UPPER",
            "camelCaseKey",
            "PascalCaseKey",
            "key$special",
        ]
        for key in special_keys:
            rule = ModelEnvironmentValidationRule(
                config_key=key,
                validation_rule="rule",
            )
            assert rule.config_key == key

    def test_config_key_with_unicode(self) -> None:
        """Test that config keys with unicode characters are valid."""
        rule = ModelEnvironmentValidationRule(
            config_key="配置键",
            validation_rule="rule",
        )
        assert rule.config_key == "配置键"

    def test_validation_rule_with_special_characters(self) -> None:
        """Test that validation rules with special characters are valid."""
        special_rules = [
            "must_be_valid_url",
            "check-value-format",
            "validate.config.value",
            "rule123",
            "RULE_UPPER",
        ]
        for rule_text in special_rules:
            rule = ModelEnvironmentValidationRule(
                config_key="key",
                validation_rule=rule_text,
            )
            assert rule.validation_rule == rule_text

    def test_allowed_values_with_various_strings(self) -> None:
        """Test that allowed_values accepts various string formats."""
        values = [
            "simple",
            "with-dash",
            "with_underscore",
            "with.dot",
            "withNumber123",
            "UPPERCASE",
            "camelCase",
            "PascalCase",
            "with spaces",
            "special@chars!",
        ]
        rule = ModelEnvironmentValidationRule(
            config_key="key",
            validation_rule="rule",
            allowed_values=values,
        )
        assert len(rule.allowed_values) == len(values)
        assert rule.allowed_values == values

    def test_allowed_values_with_unicode(self) -> None:
        """Test that allowed_values accepts unicode strings."""
        rule = ModelEnvironmentValidationRule(
            config_key="key",
            validation_rule="rule",
            allowed_values=["值1", "值2", "値3"],
        )
        assert len(rule.allowed_values) == 3

    def test_allowed_values_with_duplicates(self) -> None:
        """Test that allowed_values accepts duplicate values (no deduplication)."""
        rule = ModelEnvironmentValidationRule(
            config_key="key",
            validation_rule="rule",
            allowed_values=["value1", "value1", "value2"],
        )
        assert len(rule.allowed_values) == 3

    def test_min_and_max_value_as_numeric_values(self) -> None:
        """Test that min_value and max_value accept numeric values."""
        rule = ModelEnvironmentValidationRule(
            config_key="key",
            validation_rule="rule",
            min_value=0,
            max_value=100,
        )
        assert rule.min_value == 0
        assert rule.max_value == 100

    def test_min_and_max_value_as_negative_numbers(self) -> None:
        """Test that min_value and max_value accept negative numbers."""
        rule = ModelEnvironmentValidationRule(
            config_key="key",
            validation_rule="rule",
            min_value=-100,
            max_value=-10,
        )
        assert rule.min_value == -100
        assert rule.max_value == -10

    def test_min_and_max_value_as_floating_point(self) -> None:
        """Test that min_value and max_value accept floating point values."""
        rule = ModelEnvironmentValidationRule(
            config_key="key",
            validation_rule="rule",
            min_value=0.0,
            max_value=1.0,
        )
        assert rule.min_value == 0.0
        assert rule.max_value == 1.0

    def test_min_and_max_value_as_timestamps(self) -> None:
        """Test that min_value and max_value accept Unix timestamps."""
        rule = ModelEnvironmentValidationRule(
            config_key="key",
            validation_rule="rule",
            min_value=1672531200,  # 2023-01-01 00:00:00 UTC
            max_value=1704067199,  # 2023-12-31 23:59:59 UTC
        )
        assert rule.min_value == 1672531200
        assert rule.max_value == 1704067199

    def test_format_pattern_with_complex_regex(self) -> None:
        """Test that format_pattern accepts complex regex patterns."""
        complex_patterns = [
            r"^[A-Za-z0-9_-]+$",
            r"^\d{3}-\d{2}-\d{4}$",
            r"^(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}$",
            r"^(https?|ftp)://[^\s/$.?#].[^\s]*$",
            r"^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$",
        ]
        for pattern in complex_patterns:
            rule = ModelEnvironmentValidationRule(
                config_key="key",
                validation_rule="rule",
                format_pattern=pattern,
            )
            assert rule.format_pattern == pattern

    def test_very_long_config_key(self) -> None:
        """Test that very long config keys are valid."""
        long_key = "very_long_config_key_" * 50
        rule = ModelEnvironmentValidationRule(
            config_key=long_key,
            validation_rule="rule",
        )
        assert rule.config_key == long_key

    def test_very_long_validation_rule(self) -> None:
        """Test that very long validation rules are valid."""
        long_rule = "very_long_validation_rule_" * 50
        rule = ModelEnvironmentValidationRule(
            config_key="key",
            validation_rule=long_rule,
        )
        assert rule.validation_rule == long_rule

    def test_very_long_allowed_values_list(self) -> None:
        """Test that very long allowed_values lists are valid."""
        long_list = [f"value_{i}" for i in range(1000)]
        rule = ModelEnvironmentValidationRule(
            config_key="key",
            validation_rule="rule",
            allowed_values=long_list,
        )
        assert len(rule.allowed_values) == 1000

    def test_only_min_value_provided(self) -> None:
        """Test that only min_value can be provided without max_value."""
        rule = ModelEnvironmentValidationRule(
            config_key="key",
            validation_rule="rule",
            min_value=10,
            max_value=None,
        )
        assert rule.min_value == 10
        assert rule.max_value is None

    def test_only_max_value_provided(self) -> None:
        """Test that only max_value can be provided without min_value."""
        rule = ModelEnvironmentValidationRule(
            config_key="key",
            validation_rule="rule",
            min_value=None,
            max_value=100,
        )
        assert rule.min_value is None
        assert rule.max_value == 100

    def test_range_type_without_min_max_values(self) -> None:
        """Test that range type requires at least one of min_value or max_value."""
        with pytest.raises(ModelOnexError, match="RANGE rule requires at least"):
            ModelEnvironmentValidationRule(
                config_key="key",
                validation_rule="rule",
                rule_type=EnumEnvironmentValidationRuleType.RANGE,
            )

    def test_format_type_without_format_pattern(self) -> None:
        """Test that format type requires format_pattern to be set."""
        with pytest.raises(ModelOnexError, match="FORMAT rule requires format_pattern"):
            ModelEnvironmentValidationRule(
                config_key="key",
                validation_rule="rule",
                rule_type=EnumEnvironmentValidationRuleType.FORMAT,
            )

    def test_allowed_values_type_without_allowed_values_list(self) -> None:
        """Test that allowed_values type requires non-empty allowed_values list."""
        with pytest.raises(
            ModelOnexError, match="ALLOWED_VALUES rule requires non-empty"
        ):
            ModelEnvironmentValidationRule(
                config_key="key",
                validation_rule="rule",
                rule_type=EnumEnvironmentValidationRuleType.ALLOWED_VALUES,
                allowed_values=[],
            )


class TestModelEnvironmentValidationRuleFieldCombinationValidation:
    """Test validation of field combinations based on rule_type."""

    def test_range_type_with_only_min_value_is_valid(self) -> None:
        """Test that RANGE rule with only min_value is valid."""
        rule = ModelEnvironmentValidationRule(
            config_key="port",
            validation_rule="must_be_above_minimum",
            rule_type=EnumEnvironmentValidationRuleType.RANGE,
            min_value=1024,
        )
        assert rule.rule_type == EnumEnvironmentValidationRuleType.RANGE
        assert rule.min_value == 1024
        assert rule.max_value is None

    def test_range_type_with_only_max_value_is_valid(self) -> None:
        """Test that RANGE rule with only max_value is valid."""
        rule = ModelEnvironmentValidationRule(
            config_key="timeout",
            validation_rule="must_be_below_maximum",
            rule_type=EnumEnvironmentValidationRuleType.RANGE,
            max_value=30000,
        )
        assert rule.rule_type == EnumEnvironmentValidationRuleType.RANGE
        assert rule.min_value is None
        assert rule.max_value == 30000

    def test_range_type_with_both_min_and_max_is_valid(self) -> None:
        """Test that RANGE rule with both min_value and max_value is valid."""
        rule = ModelEnvironmentValidationRule(
            config_key="port",
            validation_rule="must_be_in_range",
            rule_type=EnumEnvironmentValidationRuleType.RANGE,
            min_value=1024,
            max_value=65535,
        )
        assert rule.rule_type == EnumEnvironmentValidationRuleType.RANGE
        assert rule.min_value == 1024
        assert rule.max_value == 65535

    def test_range_type_without_any_bounds_raises_error(self) -> None:
        """Test that RANGE rule without min_value or max_value raises error."""
        with pytest.raises(
            ModelOnexError, match="RANGE rule requires at least min_value or max_value"
        ):
            ModelEnvironmentValidationRule(
                config_key="value",
                validation_rule="must_be_in_range",
                rule_type=EnumEnvironmentValidationRuleType.RANGE,
            )

    def test_format_type_with_format_pattern_is_valid(self) -> None:
        """Test that FORMAT rule with format_pattern is valid."""
        rule = ModelEnvironmentValidationRule(
            config_key="api_key",
            validation_rule="must_match_pattern",
            rule_type=EnumEnvironmentValidationRuleType.FORMAT,
            format_pattern=r"^[A-Za-z0-9]{32}$",
        )
        assert rule.rule_type == EnumEnvironmentValidationRuleType.FORMAT
        assert rule.format_pattern == r"^[A-Za-z0-9]{32}$"

    def test_format_type_without_format_pattern_raises_error(self) -> None:
        """Test that FORMAT rule without format_pattern raises error."""
        with pytest.raises(
            ModelOnexError, match="FORMAT rule requires format_pattern to be set"
        ):
            ModelEnvironmentValidationRule(
                config_key="email",
                validation_rule="must_match_format",
                rule_type=EnumEnvironmentValidationRuleType.FORMAT,
            )

    def test_format_type_with_empty_format_pattern_raises_error(self) -> None:
        """Test that FORMAT rule with empty format_pattern raises error."""
        with pytest.raises(
            ModelOnexError, match="FORMAT rule requires format_pattern to be set"
        ):
            ModelEnvironmentValidationRule(
                config_key="email",
                validation_rule="must_match_format",
                rule_type=EnumEnvironmentValidationRuleType.FORMAT,
                format_pattern="",
            )

    def test_allowed_values_type_with_single_value_is_valid(self) -> None:
        """Test that ALLOWED_VALUES rule with single value is valid."""
        rule = ModelEnvironmentValidationRule(
            config_key="env",
            validation_rule="must_be_production",
            rule_type=EnumEnvironmentValidationRuleType.ALLOWED_VALUES,
            allowed_values=["production"],
        )
        assert rule.rule_type == EnumEnvironmentValidationRuleType.ALLOWED_VALUES
        assert rule.allowed_values == ["production"]

    def test_allowed_values_type_with_multiple_values_is_valid(self) -> None:
        """Test that ALLOWED_VALUES rule with multiple values is valid."""
        rule = ModelEnvironmentValidationRule(
            config_key="log_level",
            validation_rule="must_be_valid_level",
            rule_type=EnumEnvironmentValidationRuleType.ALLOWED_VALUES,
            allowed_values=["DEBUG", "INFO", "WARN", "ERROR"],
        )
        assert rule.rule_type == EnumEnvironmentValidationRuleType.ALLOWED_VALUES
        assert len(rule.allowed_values) == 4

    def test_allowed_values_type_with_empty_list_raises_error(self) -> None:
        """Test that ALLOWED_VALUES rule with empty list raises error."""
        with pytest.raises(
            ModelOnexError,
            match="ALLOWED_VALUES rule requires non-empty allowed_values list",
        ):
            ModelEnvironmentValidationRule(
                config_key="status",
                validation_rule="must_be_in_list",
                rule_type=EnumEnvironmentValidationRuleType.ALLOWED_VALUES,
                allowed_values=[],
            )

    def test_allowed_values_type_without_list_raises_error(self) -> None:
        """Test that ALLOWED_VALUES rule without allowed_values raises error."""
        with pytest.raises(
            ModelOnexError,
            match="ALLOWED_VALUES rule requires non-empty allowed_values list",
        ):
            ModelEnvironmentValidationRule(
                config_key="status",
                validation_rule="must_be_in_list",
                rule_type=EnumEnvironmentValidationRuleType.ALLOWED_VALUES,
            )

    def test_value_check_type_without_special_fields_is_valid(self) -> None:
        """Test that VALUE_CHECK rule without special fields is valid."""
        rule = ModelEnvironmentValidationRule(
            config_key="database_url",
            validation_rule="must_be_valid_url",
            rule_type=EnumEnvironmentValidationRuleType.VALUE_CHECK,
        )
        assert rule.rule_type == EnumEnvironmentValidationRuleType.VALUE_CHECK
        assert rule.allowed_values == []
        assert rule.min_value is None
        assert rule.max_value is None
        assert rule.format_pattern is None

    def test_value_check_type_with_extra_fields_is_valid(self) -> None:
        """Test that VALUE_CHECK rule with extra fields is valid (no validation)."""
        rule = ModelEnvironmentValidationRule(
            config_key="config",
            validation_rule="check_value",
            rule_type=EnumEnvironmentValidationRuleType.VALUE_CHECK,
            allowed_values=["value1"],
            min_value=10,
            max_value=100,
            format_pattern=r"^\d+$",
        )
        assert rule.rule_type == EnumEnvironmentValidationRuleType.VALUE_CHECK
        # VALUE_CHECK doesn't enforce field requirements

    def test_range_type_with_zero_as_min_value(self) -> None:
        """Test that RANGE rule accepts zero as min_value."""
        rule = ModelEnvironmentValidationRule(
            config_key="offset",
            validation_rule="must_be_non_negative",
            rule_type=EnumEnvironmentValidationRuleType.RANGE,
            min_value=0,
        )
        assert rule.min_value == 0

    def test_range_type_with_negative_bounds(self) -> None:
        """Test that RANGE rule accepts negative bounds."""
        rule = ModelEnvironmentValidationRule(
            config_key="temperature",
            validation_rule="must_be_in_celsius_range",
            rule_type=EnumEnvironmentValidationRuleType.RANGE,
            min_value=-273.15,
            max_value=1000.0,
        )
        assert rule.min_value == -273.15
        assert rule.max_value == 1000.0

    def test_format_type_with_complex_regex_pattern(self) -> None:
        """Test that FORMAT rule accepts complex regex patterns."""
        pattern = r"^(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}$"
        rule = ModelEnvironmentValidationRule(
            config_key="password",
            validation_rule="must_be_strong",
            rule_type=EnumEnvironmentValidationRuleType.FORMAT,
            format_pattern=pattern,
        )
        assert rule.format_pattern == pattern

    def test_allowed_values_with_duplicates_is_valid(self) -> None:
        """Test that ALLOWED_VALUES rule with duplicates is valid (no deduplication)."""
        rule = ModelEnvironmentValidationRule(
            config_key="status",
            validation_rule="must_be_in_list",
            rule_type=EnumEnvironmentValidationRuleType.ALLOWED_VALUES,
            allowed_values=["active", "active", "inactive"],
        )
        assert len(rule.allowed_values) == 3

    def test_allowed_values_with_unicode_strings(self) -> None:
        """Test that ALLOWED_VALUES rule accepts unicode strings."""
        rule = ModelEnvironmentValidationRule(
            config_key="locale",
            validation_rule="must_be_supported",
            rule_type=EnumEnvironmentValidationRuleType.ALLOWED_VALUES,
            allowed_values=["en", "日本語", "中文", "한국어"],
        )
        assert len(rule.allowed_values) == 4

    def test_validator_runs_on_assignment(self) -> None:
        """Test that validator runs when rule_type is changed after creation."""
        # Start with VALUE_CHECK (no requirements)
        rule = ModelEnvironmentValidationRule(
            config_key="key",
            validation_rule="rule",
            rule_type=EnumEnvironmentValidationRuleType.VALUE_CHECK,
        )

        # Changing to RANGE without bounds should raise error
        with pytest.raises(
            ModelOnexError, match="RANGE rule requires at least min_value or max_value"
        ):
            rule.rule_type = EnumEnvironmentValidationRuleType.RANGE
