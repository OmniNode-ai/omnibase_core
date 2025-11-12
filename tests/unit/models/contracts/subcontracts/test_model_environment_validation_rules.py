"""
Tests for ModelEnvironmentValidationRules.

Validates environment validation rules container configuration including
type safety, field constraints, and environment-specific rule grouping.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_environment import EnumEnvironment
from omnibase_core.enums.enum_environment_validation_rule_type import (
    EnumEnvironmentValidationRuleType,
)
from omnibase_core.models.contracts.subcontracts.model_environment_validation_rule import (
    ModelEnvironmentValidationRule,
)
from omnibase_core.models.contracts.subcontracts.model_environment_validation_rules import (
    ModelEnvironmentValidationRules,
)


class TestModelEnvironmentValidationRulesValidation:
    """Test validation rules for environment validation rules container."""

    def test_valid_rules_for_development_environment(self) -> None:
        """Test that rules for development environment are valid."""
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.DEVELOPMENT,
            validation_rules=[
                ModelEnvironmentValidationRule(
                    config_key="debug_mode",
                    validation_rule="must_be_true",
                ),
            ],
        )
        assert rules.environment == EnumEnvironment.DEVELOPMENT
        assert len(rules.validation_rules) == 1

    def test_valid_rules_for_production_environment(self) -> None:
        """Test that rules for production environment are valid."""
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.PRODUCTION,
            validation_rules=[
                ModelEnvironmentValidationRule(
                    config_key="debug_mode",
                    validation_rule="must_be_false",
                ),
            ],
        )
        assert rules.environment == EnumEnvironment.PRODUCTION

    def test_valid_rules_with_multiple_validation_rules(self) -> None:
        """Test that multiple validation rules are valid."""
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.STAGING,
            validation_rules=[
                ModelEnvironmentValidationRule(
                    config_key="database_url",
                    validation_rule="must_be_postgresql",
                ),
                ModelEnvironmentValidationRule(
                    config_key="redis_url",
                    validation_rule="must_be_redis",
                ),
                ModelEnvironmentValidationRule(
                    config_key="log_level",
                    validation_rule="must_be_info_or_warn",
                ),
            ],
        )
        assert len(rules.validation_rules) == 3

    def test_valid_rules_with_empty_validation_rules_list(self) -> None:
        """Test that empty validation rules list is valid."""
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.TESTING,
            validation_rules=[],
        )
        assert rules.validation_rules == []

    def test_valid_rules_with_inherit_from_default_true(self) -> None:
        """Test that inherit_from_default=True is valid."""
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.PRODUCTION,
            inherit_from_default=True,
        )
        assert rules.inherit_from_default is True

    def test_valid_rules_with_inherit_from_default_false(self) -> None:
        """Test that inherit_from_default=False is valid."""
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.PRODUCTION,
            inherit_from_default=False,
        )
        assert rules.inherit_from_default is False

    def test_valid_rules_with_override_default_true(self) -> None:
        """Test that override_default=True is valid."""
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.PRODUCTION,
            override_default=True,
        )
        assert rules.override_default is True

    def test_valid_rules_with_override_default_false(self) -> None:
        """Test that override_default=False is valid."""
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.PRODUCTION,
            override_default=False,
        )
        assert rules.override_default is False

    def test_valid_rules_with_both_flags_set(self) -> None:
        """Test that both inherit and override flags can be set (MERGE_WITH_OVERRIDE mode).

        This triggers a UserWarning as it's an advanced pattern.
        """
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            rules = ModelEnvironmentValidationRules(
                environment=EnumEnvironment.STAGING,
                inherit_from_default=True,
                override_default=True,
            )
            assert rules.inherit_from_default is True
            assert rules.override_default is True
            # Verify warning was raised
            assert len(w) == 1
            assert issubclass(w[0].category, UserWarning)
            assert "MERGE_WITH_OVERRIDE" in str(w[0].message)


class TestModelEnvironmentValidationRulesCreation:
    """Test creation and field constraints."""

    def test_required_fields(self) -> None:
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            ModelEnvironmentValidationRules()  # type: ignore[call-arg]

    def test_default_values(self) -> None:
        """Test default field values."""
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.DEVELOPMENT,
        )
        assert rules.validation_rules == []
        assert rules.inherit_from_default is True
        assert rules.override_default is False

    def test_optional_fields(self) -> None:
        """Test optional field assignment."""
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.PRODUCTION,
            validation_rules=[
                ModelEnvironmentValidationRule(
                    config_key="key1",
                    validation_rule="rule1",
                ),
            ],
            inherit_from_default=False,
            override_default=True,
        )
        assert len(rules.validation_rules) == 1
        assert rules.inherit_from_default is False
        assert rules.override_default is True

    def test_enum_values_for_environment(self) -> None:
        """Test that environment accepts all valid enum values."""
        for env in EnumEnvironment:
            rules = ModelEnvironmentValidationRules(
                environment=env,
            )
            assert rules.environment == env


class TestModelEnvironmentValidationRulesEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_rules_with_many_validation_rules(self) -> None:
        """Test that many validation rules are valid."""
        validation_rules = [
            ModelEnvironmentValidationRule(
                config_key=f"key_{i}",
                validation_rule=f"rule_{i}",
            )
            for i in range(100)
        ]
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.PRODUCTION,
            validation_rules=validation_rules,
        )
        assert len(rules.validation_rules) == 100

    def test_rules_with_complex_validation_rules(self) -> None:
        """Test that complex validation rules are valid."""
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.PRODUCTION,
            validation_rules=[
                ModelEnvironmentValidationRule(
                    config_key="api_key",
                    validation_rule="must_match_pattern",
                    rule_type=EnumEnvironmentValidationRuleType.FORMAT,
                    format_pattern=r"^[A-Za-z0-9]{32}$",
                ),
                ModelEnvironmentValidationRule(
                    config_key="port",
                    validation_rule="must_be_in_range",
                    rule_type=EnumEnvironmentValidationRuleType.RANGE,
                    min_value=1024,
                    max_value=65535,
                ),
                ModelEnvironmentValidationRule(
                    config_key="log_level",
                    validation_rule="must_be_in_list",
                    rule_type=EnumEnvironmentValidationRuleType.ALLOWED_VALUES,
                    allowed_values=["INFO", "WARN", "ERROR"],
                ),
            ],
        )
        assert len(rules.validation_rules) == 3

    def test_rules_with_duplicate_config_keys(self) -> None:
        """Test that duplicate config keys are allowed (no uniqueness constraint)."""
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.STAGING,
            validation_rules=[
                ModelEnvironmentValidationRule(
                    config_key="database_url",
                    validation_rule="rule1",
                ),
                ModelEnvironmentValidationRule(
                    config_key="database_url",  # Duplicate key
                    validation_rule="rule2",
                ),
            ],
        )
        assert len(rules.validation_rules) == 2

    def test_local_environment(self) -> None:
        """Test that LOCAL environment is valid."""
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.LOCAL,
        )
        assert rules.environment == EnumEnvironment.LOCAL

    def test_integration_environment(self) -> None:
        """Test that INTEGRATION environment is valid."""
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.INTEGRATION,
        )
        assert rules.environment == EnumEnvironment.INTEGRATION

    def test_preview_environment(self) -> None:
        """Test that PREVIEW environment is valid."""
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.PREVIEW,
        )
        assert rules.environment == EnumEnvironment.PREVIEW

    def test_sandbox_environment(self) -> None:
        """Test that SANDBOX environment is valid."""
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.SANDBOX,
        )
        assert rules.environment == EnumEnvironment.SANDBOX

    def test_inherit_true_override_false(self) -> None:
        """Test EXTEND mode: inherit from default, don't override (DEFAULT - RECOMMENDED).

        Inheritance Mode: EXTEND
        - Start with default rules
        - Add environment-specific rules
        - Environment rules complement defaults
        """
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.STAGING,
            inherit_from_default=True,
            override_default=False,
        )
        assert rules.inherit_from_default is True
        assert rules.override_default is False
        assert hasattr(rules, "_inheritance_mode")
        assert rules._inheritance_mode == "EXTEND"  # type: ignore[attr-defined]

    def test_inherit_false_override_true(self) -> None:
        """Test REPLACE mode: don't inherit, but override default.

        Inheritance Mode: REPLACE
        - Completely replace default rules
        - Only use environment-specific rules
        - Ignore all defaults
        """
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.PRODUCTION,
            inherit_from_default=False,
            override_default=True,
        )
        assert rules.inherit_from_default is False
        assert rules.override_default is True
        assert hasattr(rules, "_inheritance_mode")
        assert rules._inheritance_mode == "REPLACE"  # type: ignore[attr-defined]

    def test_inherit_false_override_false(self) -> None:
        """Test ISOLATED mode: don't inherit, don't override.

        Inheritance Mode: ISOLATED
        - Use only environment-specific rules
        - No interaction with defaults
        - Standalone rule set
        """
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.LOCAL,
            inherit_from_default=False,
            override_default=False,
        )
        assert rules.inherit_from_default is False
        assert rules.override_default is False
        assert hasattr(rules, "_inheritance_mode")
        assert rules._inheritance_mode == "ISOLATED"  # type: ignore[attr-defined]

    def test_inherit_true_override_true(self) -> None:
        """Test MERGE_WITH_OVERRIDE mode: inherit and override (ADVANCED).

        Inheritance Mode: MERGE_WITH_OVERRIDE
        - Start with default rules
        - Environment rules override conflicting defaults
        - Non-conflicting defaults preserved
        - Triggers UserWarning due to complexity
        """
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            rules = ModelEnvironmentValidationRules(
                environment=EnumEnvironment.STAGING,
                inherit_from_default=True,
                override_default=True,
            )
            assert rules.inherit_from_default is True
            assert rules.override_default is True
            assert hasattr(rules, "_inheritance_mode")
            assert rules._inheritance_mode == "MERGE_WITH_OVERRIDE"  # type: ignore[attr-defined]
            # Verify warning was raised
            assert len(w) == 1
            assert issubclass(w[0].category, UserWarning)
            assert "MERGE_WITH_OVERRIDE" in str(w[0].message)

    def test_validation_rules_with_all_rule_types(self) -> None:
        """Test that all rule types can be used in validation_rules."""
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.PRODUCTION,
            validation_rules=[
                ModelEnvironmentValidationRule(
                    config_key="key1",
                    validation_rule="rule1",
                    rule_type=EnumEnvironmentValidationRuleType.VALUE_CHECK,
                ),
                ModelEnvironmentValidationRule(
                    config_key="key2",
                    validation_rule="rule2",
                    rule_type=EnumEnvironmentValidationRuleType.FORMAT,
                    format_pattern="[a-z]+",
                ),
                ModelEnvironmentValidationRule(
                    config_key="key3",
                    validation_rule="rule3",
                    rule_type=EnumEnvironmentValidationRuleType.RANGE,
                    min_value=0.0,
                    max_value=100.0,
                ),
                ModelEnvironmentValidationRule(
                    config_key="key4",
                    validation_rule="rule4",
                    rule_type=EnumEnvironmentValidationRuleType.ALLOWED_VALUES,
                    allowed_values=["value1", "value2", "value3"],
                ),
            ],
        )
        assert len(rules.validation_rules) == 4
        rule_types = {rule.rule_type for rule in rules.validation_rules}
        assert len(rule_types) == 4

    def test_production_like_environments_with_strict_rules(self) -> None:
        """Test production-like environments with strict validation rules."""
        for env in [EnumEnvironment.PRODUCTION, EnumEnvironment.STAGING]:
            rules = ModelEnvironmentValidationRules(
                environment=env,
                validation_rules=[
                    ModelEnvironmentValidationRule(
                        config_key="debug_mode",
                        validation_rule="must_be_false",
                    ),
                    ModelEnvironmentValidationRule(
                        config_key="ssl_enabled",
                        validation_rule="must_be_true",
                    ),
                ],
                inherit_from_default=False,
                override_default=True,
            )
            assert rules.environment == env
            assert rules.override_default is True

    def test_development_like_environments_with_relaxed_rules(self) -> None:
        """Test development-like environments with relaxed validation rules."""
        for env in [
            EnumEnvironment.DEVELOPMENT,
            EnumEnvironment.LOCAL,
            EnumEnvironment.SANDBOX,
        ]:
            rules = ModelEnvironmentValidationRules(
                environment=env,
                validation_rules=[
                    ModelEnvironmentValidationRule(
                        config_key="debug_mode",
                        validation_rule="can_be_any_value",
                    ),
                ],
                inherit_from_default=True,
                override_default=False,
            )
            assert rules.environment == env
            assert rules.inherit_from_default is True

    def test_empty_rules_with_inheritance(self) -> None:
        """Test empty rules list with inheritance enabled."""
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.STAGING,
            validation_rules=[],
            inherit_from_default=True,
        )
        assert len(rules.validation_rules) == 0
        assert rules.inherit_from_default is True

    def test_empty_rules_with_override(self) -> None:
        """Test empty rules list with override enabled."""
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.PRODUCTION,
            validation_rules=[],
            override_default=True,
        )
        assert len(rules.validation_rules) == 0
        assert rules.override_default is True

    def test_validation_rules_order_preservation(self) -> None:
        """Test that validation_rules list preserves order."""
        keys = [f"key_{i}" for i in range(20)]
        validation_rules = [
            ModelEnvironmentValidationRule(
                config_key=key,
                validation_rule=f"rule_{key}",
            )
            for key in keys
        ]
        rules = ModelEnvironmentValidationRules(
            environment=EnumEnvironment.TESTING,
            validation_rules=validation_rules,
        )
        result_keys = [rule.config_key for rule in rules.validation_rules]
        assert result_keys == keys


class TestModelEnvironmentValidationRulesInheritanceModes:
    """Test inheritance mode validation and flag behavior."""

    def test_extend_mode_no_warning(self) -> None:
        """Test EXTEND mode (inherit=True, override=False) doesn't trigger warning."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            rules = ModelEnvironmentValidationRules(
                environment=EnumEnvironment.DEVELOPMENT,
                inherit_from_default=True,
                override_default=False,
            )
            assert rules._inheritance_mode == "EXTEND"  # type: ignore[attr-defined]
            assert len(w) == 0  # No warnings

    def test_replace_mode_no_warning(self) -> None:
        """Test REPLACE mode (inherit=False, override=True) doesn't trigger warning."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            rules = ModelEnvironmentValidationRules(
                environment=EnumEnvironment.PRODUCTION,
                inherit_from_default=False,
                override_default=True,
            )
            assert rules._inheritance_mode == "REPLACE"  # type: ignore[attr-defined]
            assert len(w) == 0  # No warnings

    def test_isolated_mode_no_warning(self) -> None:
        """Test ISOLATED mode (inherit=False, override=False) doesn't trigger warning."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            rules = ModelEnvironmentValidationRules(
                environment=EnumEnvironment.TESTING,
                inherit_from_default=False,
                override_default=False,
            )
            assert rules._inheritance_mode == "ISOLATED"  # type: ignore[attr-defined]
            assert len(w) == 0  # No warnings

    def test_merge_with_override_mode_triggers_warning(self) -> None:
        """Test MERGE_WITH_OVERRIDE mode (inherit=True, override=True) triggers warning."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            rules = ModelEnvironmentValidationRules(
                environment=EnumEnvironment.STAGING,
                inherit_from_default=True,
                override_default=True,
            )
            assert rules._inheritance_mode == "MERGE_WITH_OVERRIDE"  # type: ignore[attr-defined]
            assert len(w) == 1
            assert issubclass(w[0].category, UserWarning)
            assert "MERGE_WITH_OVERRIDE" in str(w[0].message)
            assert "advanced pattern" in str(w[0].message).lower()

    def test_inheritance_mode_internal_attribute(self) -> None:
        """Test that _inheritance_mode is set correctly for all combinations."""
        test_cases = [
            (True, False, "EXTEND"),
            (False, True, "REPLACE"),
            (False, False, "ISOLATED"),
            (True, True, "MERGE_WITH_OVERRIDE"),
        ]

        import warnings

        for inherit, override, expected_mode in test_cases:
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                rules = ModelEnvironmentValidationRules(
                    environment=EnumEnvironment.STAGING,
                    inherit_from_default=inherit,
                    override_default=override,
                )
                assert hasattr(rules, "_inheritance_mode")
                assert rules._inheritance_mode == expected_mode  # type: ignore[attr-defined]

    def test_warning_message_includes_environment(self) -> None:
        """Test that warning message includes the environment name."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            rules = ModelEnvironmentValidationRules(
                environment=EnumEnvironment.PRODUCTION,
                inherit_from_default=True,
                override_default=True,
            )
            assert len(w) == 1
            # Environment value is lowercase in the message
            assert "production" in str(w[0].message).lower()

    def test_warning_includes_recommendation(self) -> None:
        """Test that warning message includes recommended alternative."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            rules = ModelEnvironmentValidationRules(
                environment=EnumEnvironment.STAGING,
                inherit_from_default=True,
                override_default=True,
            )
            assert len(w) == 1
            message = str(w[0].message)
            assert "Recommended" in message or "recommended" in message
            assert "EXTEND" in message
