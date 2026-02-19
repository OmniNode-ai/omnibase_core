# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelLogLevelOverride.

Comprehensive test coverage for log level override model including:
- Field validation and constraints
- Enum validation for log levels
- Priority bounds and defaults
- Edge cases and error scenarios
- ConfigDict behavior
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)

from omnibase_core.enums.enum_log_level import EnumLogLevel
from omnibase_core.models.contracts.subcontracts.model_log_level_override import (
    ModelLogLevelOverride,
)


@pytest.mark.unit
class TestModelLogLevelOverrideBasics:
    """Test basic model instantiation and defaults."""

    def test_minimal_instantiation(self):
        """Test model can be instantiated with minimal required fields."""
        override = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="my.module",
            log_level=EnumLogLevel.DEBUG,
        )

        assert override.logger_name == "my.module"
        assert override.log_level == EnumLogLevel.DEBUG
        assert override.apply_to_children is True
        assert override.override_priority == 100
        assert override.description is None

    def test_full_instantiation(self):
        """Test model with all fields specified."""
        override = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="app.service.auth",
            log_level=EnumLogLevel.WARNING,
            apply_to_children=False,
            override_priority=500,
            description="Reduce auth logging noise",
        )

        assert override.logger_name == "app.service.auth"
        assert override.log_level == EnumLogLevel.WARNING
        assert override.apply_to_children is False
        assert override.override_priority == 500
        assert override.description == "Reduce auth logging noise"

    def test_default_values(self):
        """Test default values are correctly applied."""
        override = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="test",
            log_level=EnumLogLevel.INFO,
        )

        # Defaults from model
        assert override.apply_to_children is True
        assert override.override_priority == 100
        assert override.description is None


@pytest.mark.unit
class TestModelLogLevelOverrideValidation:
    """Test field validation and constraints."""

    def test_logger_name_required(self):
        """Test logger_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelLogLevelOverride(
                version=DEFAULT_VERSION,
                log_level=EnumLogLevel.INFO,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("logger_name",) for e in errors)

    def test_logger_name_min_length(self):
        """Test logger_name must have minimum length."""
        # Empty string should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelLogLevelOverride(
                version=DEFAULT_VERSION,
                logger_name="",
                log_level=EnumLogLevel.INFO,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("logger_name",) for e in errors)

    def test_logger_name_valid_values(self):
        """Test various valid logger names."""
        valid_names = [
            "root",
            "app",
            "app.module",
            "app.module.submodule",
            "my_logger",
            "logger123",
            "com.company.product.feature",
        ]

        for name in valid_names:
            override = ModelLogLevelOverride(
                version=DEFAULT_VERSION,
                logger_name=name,
                log_level=EnumLogLevel.DEBUG,
            )
            assert override.logger_name == name


@pytest.mark.unit
class TestModelLogLevelOverridePatternValidation:
    """Test logger_name pattern validation (dotted notation)."""

    def test_logger_name_pattern_valid_simple(self):
        """Test valid simple logger names (no dots)."""
        valid_names = [
            "myapp",
            "my_app",
            "app123",
            "_private",
            "logger",
            "a",  # Single character
            "_",  # Single underscore
        ]

        for name in valid_names:
            override = ModelLogLevelOverride(
                version=DEFAULT_VERSION,
                logger_name=name,
                log_level=EnumLogLevel.DEBUG,
            )
            assert override.logger_name == name

    def test_logger_name_pattern_valid_dotted(self):
        """Test valid dotted notation logger names."""
        valid_names = [
            "myapp.module",
            "myapp.module.submodule",
            "app_v2.component_a",
            "logger123.component456",
            "_private.module",
            "a.b.c.d.e.f",  # Deep hierarchy
            "module_v2.sub_module_v3",
        ]

        for name in valid_names:
            override = ModelLogLevelOverride(
                version=DEFAULT_VERSION,
                logger_name=name,
                log_level=EnumLogLevel.DEBUG,
            )
            assert override.logger_name == name

    def test_logger_name_pattern_invalid_uppercase(self):
        """Test pattern rejects uppercase letters."""
        invalid_names = [
            "MyApp",
            "myApp",
            "MYAPP",
            "myapp.Module",
            "myapp.module.SubModule",
        ]

        for name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                ModelLogLevelOverride(
                    version=DEFAULT_VERSION,
                    logger_name=name,
                    log_level=EnumLogLevel.INFO,
                )
            errors = exc_info.value.errors()
            assert any(e["loc"] == ("logger_name",) for e in errors)
            assert any("pattern" in str(e["type"]).lower() for e in errors)

    def test_logger_name_pattern_invalid_special_chars(self):
        """Test pattern rejects invalid special characters."""
        invalid_names = [
            "my-app",  # Hyphen
            "my app",  # Space
            "my/app",  # Slash
            "my@app",  # At symbol
            "my#app",  # Hash
            "my$app",  # Dollar
            "my%app",  # Percent
            "my&app",  # Ampersand
        ]

        for name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                ModelLogLevelOverride(
                    version=DEFAULT_VERSION,
                    logger_name=name,
                    log_level=EnumLogLevel.INFO,
                )
            errors = exc_info.value.errors()
            assert any(e["loc"] == ("logger_name",) for e in errors)

    def test_logger_name_pattern_invalid_start_with_number(self):
        """Test pattern rejects names starting with number."""
        invalid_names = [
            "123app",
            "1myapp",
            "9logger",
        ]

        for name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                ModelLogLevelOverride(
                    version=DEFAULT_VERSION,
                    logger_name=name,
                    log_level=EnumLogLevel.INFO,
                )
            errors = exc_info.value.errors()
            assert any(e["loc"] == ("logger_name",) for e in errors)

    def test_logger_name_pattern_invalid_start_with_dot(self):
        """Test pattern rejects names starting with dot."""
        with pytest.raises(ValidationError) as exc_info:
            ModelLogLevelOverride(
                version=DEFAULT_VERSION,
                logger_name=".myapp",
                log_level=EnumLogLevel.INFO,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("logger_name",) for e in errors)

    def test_logger_name_pattern_invalid_end_with_dot(self):
        """Test pattern rejects names ending with dot."""
        with pytest.raises(ValidationError) as exc_info:
            ModelLogLevelOverride(
                version=DEFAULT_VERSION,
                logger_name="myapp.",
                log_level=EnumLogLevel.INFO,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("logger_name",) for e in errors)

    def test_logger_name_pattern_invalid_double_dot(self):
        """Test pattern rejects consecutive dots."""
        invalid_names = [
            "myapp..module",
            "app...logger",
            "a..b",
        ]

        for name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                ModelLogLevelOverride(
                    version=DEFAULT_VERSION,
                    logger_name=name,
                    log_level=EnumLogLevel.INFO,
                )
            errors = exc_info.value.errors()
            assert any(e["loc"] == ("logger_name",) for e in errors)

    def test_logger_name_pattern_segment_starting_with_number(self):
        """Test pattern rejects segments starting with number."""
        invalid_names = [
            "myapp.123module",
            "app.1logger",
            "valid.9bad",
        ]

        for name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                ModelLogLevelOverride(
                    version=DEFAULT_VERSION,
                    logger_name=name,
                    log_level=EnumLogLevel.INFO,
                )
            errors = exc_info.value.errors()
            assert any(e["loc"] == ("logger_name",) for e in errors)

    def test_logger_name_pattern_numbers_allowed_after_letters(self):
        """Test pattern allows numbers after letters/underscores."""
        valid_names = [
            "app123",
            "module_v2",
            "logger_123",
            "comp1.mod2.sub3",
        ]

        for name in valid_names:
            override = ModelLogLevelOverride(
                version=DEFAULT_VERSION,
                logger_name=name,
                log_level=EnumLogLevel.DEBUG,
            )
            assert override.logger_name == name

    def test_logger_name_pattern_real_world_examples(self):
        """Test pattern with real-world logger names."""
        real_world_names = [
            "urllib3",
            "urllib3.connectionpool",
            "requests.packages.urllib3",
            "django.db.backends",
            "sqlalchemy.engine",
            "boto3.resources.base",
            "paramiko.transport",
        ]

        for name in real_world_names:
            override = ModelLogLevelOverride(
                version=DEFAULT_VERSION,
                logger_name=name,
                log_level=EnumLogLevel.WARNING,
            )
            assert override.logger_name == name

    def test_log_level_required(self):
        """Test log_level is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelLogLevelOverride(
                version=DEFAULT_VERSION,
                logger_name="test",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("log_level",) for e in errors)

    def test_log_level_enum_values(self):
        """Test all valid log level enum values."""
        valid_levels = [
            EnumLogLevel.TRACE,
            EnumLogLevel.DEBUG,
            EnumLogLevel.INFO,
            EnumLogLevel.WARNING,
            EnumLogLevel.ERROR,
            EnumLogLevel.CRITICAL,
            EnumLogLevel.FATAL,
            EnumLogLevel.SUCCESS,
            EnumLogLevel.UNKNOWN,
        ]

        for level in valid_levels:
            override = ModelLogLevelOverride(
                version=DEFAULT_VERSION,
                logger_name="test",
                log_level=level,
            )
            assert override.log_level == level

    def test_log_level_invalid_value(self):
        """Test invalid log level raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelLogLevelOverride(
                version=DEFAULT_VERSION,
                logger_name="test",
                log_level="invalid_level",  # type: ignore[arg-type]
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("log_level",) for e in errors)

    def test_override_priority_bounds(self):
        """Test override_priority validates bounds."""
        # Valid values
        ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="test",
            log_level=EnumLogLevel.INFO,
            override_priority=0,  # Min
        )
        ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="test",
            log_level=EnumLogLevel.INFO,
            override_priority=500,
        )
        ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="test",
            log_level=EnumLogLevel.INFO,
            override_priority=1000,  # Max
        )

        # Below minimum
        with pytest.raises(ValidationError) as exc_info:
            ModelLogLevelOverride(
                version=DEFAULT_VERSION,
                logger_name="test",
                log_level=EnumLogLevel.INFO,
                override_priority=-1,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("override_priority",) for e in errors)

        # Above maximum
        with pytest.raises(ValidationError) as exc_info:
            ModelLogLevelOverride(
                version=DEFAULT_VERSION,
                logger_name="test",
                log_level=EnumLogLevel.INFO,
                override_priority=1001,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("override_priority",) for e in errors)

    def test_apply_to_children_boolean(self):
        """Test apply_to_children accepts boolean values."""
        override_true = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="test",
            log_level=EnumLogLevel.INFO,
            apply_to_children=True,
        )
        assert override_true.apply_to_children is True

        override_false = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="test",
            log_level=EnumLogLevel.INFO,
            apply_to_children=False,
        )
        assert override_false.apply_to_children is False

    def test_description_optional(self):
        """Test description is optional."""
        override = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="test",
            log_level=EnumLogLevel.INFO,
            description=None,
        )
        assert override.description is None

        override_with_desc = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="test",
            log_level=EnumLogLevel.INFO,
            description="Test description",
        )
        assert override_with_desc.description == "Test description"


@pytest.mark.unit
class TestModelLogLevelOverrideEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_minimum_priority_override(self):
        """Test override with minimum priority."""
        override = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="low.priority.logger",
            log_level=EnumLogLevel.TRACE,
            override_priority=0,
        )

        assert override.override_priority == 0

    def test_maximum_priority_override(self):
        """Test override with maximum priority."""
        override = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="high.priority.logger",
            log_level=EnumLogLevel.FATAL,
            override_priority=1000,
        )

        assert override.override_priority == 1000

    def test_root_logger_override(self):
        """Test override for root logger."""
        override = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="root",
            log_level=EnumLogLevel.WARNING,
            apply_to_children=True,
        )

        assert override.logger_name == "root"
        assert override.apply_to_children is True

    def test_deep_hierarchical_logger_name(self):
        """Test override for deeply nested logger."""
        override = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="app.service.module.submodule.component.feature",
            log_level=EnumLogLevel.DEBUG,
        )

        assert override.logger_name == "app.service.module.submodule.component.feature"

    def test_isolated_logger_no_children(self):
        """Test override that doesn't apply to children."""
        override = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="isolated.logger",
            log_level=EnumLogLevel.ERROR,
            apply_to_children=False,
        )

        assert override.apply_to_children is False

    def test_long_description(self):
        """Test override with long description."""
        long_desc = "A" * 500
        override = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="test",
            log_level=EnumLogLevel.INFO,
            description=long_desc,
        )

        assert override.description == long_desc
        assert len(override.description) == 500

    def test_special_log_levels(self):
        """Test special log levels like SUCCESS and UNKNOWN."""
        success_override = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="success.logger",
            log_level=EnumLogLevel.SUCCESS,
        )
        assert success_override.log_level == EnumLogLevel.SUCCESS

        unknown_override = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="unknown.logger",
            log_level=EnumLogLevel.UNKNOWN,
        )
        assert unknown_override.log_level == EnumLogLevel.UNKNOWN

    def test_multiple_overrides_same_logger_different_priorities(self):
        """Test multiple override instances for same logger with different priorities."""
        override1 = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="shared.logger",
            log_level=EnumLogLevel.INFO,
            override_priority=100,
        )

        override2 = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="shared.logger",
            log_level=EnumLogLevel.DEBUG,
            override_priority=200,
        )

        assert override1.logger_name == override2.logger_name
        assert override1.override_priority < override2.override_priority


@pytest.mark.unit
class TestModelLogLevelOverrideConfigDict:
    """Test ConfigDict behavior."""

    def test_extra_fields_ignored(self):
        """Test extra fields are ignored per ConfigDict."""
        override = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="test",
            log_level=EnumLogLevel.INFO,
            unknown_field="should_be_ignored",  # type: ignore[call-arg]
        )

        assert override.logger_name == "test"
        assert not hasattr(override, "unknown_field")

    def test_validate_assignment(self):
        """Test assignment validation is enabled."""
        override = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="test",
            log_level=EnumLogLevel.INFO,
        )

        # Valid assignment
        override.override_priority = 500
        assert override.override_priority == 500

        # Invalid assignment should raise
        with pytest.raises(ValidationError):
            override.override_priority = -1

        with pytest.raises(ValidationError):
            override.override_priority = 1001

    def test_enum_values_not_coerced(self):
        """Test use_enum_values is False - enums stay as enum objects."""
        override = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="test",
            log_level=EnumLogLevel.DEBUG,
        )

        # Should be enum object, not string
        assert isinstance(override.log_level, EnumLogLevel)
        assert override.log_level == EnumLogLevel.DEBUG

    def test_model_serialization(self):
        """Test model can be serialized and deserialized."""
        original = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="app.service",
            log_level=EnumLogLevel.WARNING,
            apply_to_children=False,
            override_priority=750,
            description="Production override",
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize
        restored = ModelLogLevelOverride(**data)

        assert restored.logger_name == original.logger_name
        assert restored.log_level == original.log_level
        assert restored.apply_to_children == original.apply_to_children
        assert restored.override_priority == original.override_priority
        assert restored.description == original.description

    def test_json_serialization(self):
        """Test model can be serialized to JSON."""
        override = ModelLogLevelOverride(
            version=DEFAULT_VERSION,
            logger_name="test",
            log_level=EnumLogLevel.ERROR,
        )

        json_str = override.model_dump_json()
        assert "test" in json_str
        assert "error" in json_str.lower()


@pytest.mark.unit
class TestModelLogLevelOverrideDocumentation:
    """Test documentation and interface guarantees."""

    def test_docstring_present(self):
        """Test model has comprehensive docstring."""
        assert ModelLogLevelOverride.__doc__ is not None
        assert len(ModelLogLevelOverride.__doc__) > 50

    def test_field_descriptions(self):
        """Test all fields have descriptions."""
        schema = ModelLogLevelOverride.model_json_schema()

        for field_name, field_info in schema.get("properties", {}).items():
            assert "description" in field_info, (
                f"Field {field_name} missing description"
            )
