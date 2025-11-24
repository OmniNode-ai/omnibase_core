"""
Tests for ModelValidationSchemaRule.

Validates validation schema rule configuration including
format validation for different rule types (regex, json_schema, range, enum).
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)

from omnibase_core.enums.enum_validation_rule_type import EnumValidationRuleType
from omnibase_core.models.contracts.subcontracts.model_validation_schema_rule import (
    ModelValidationSchemaRule,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class TestModelValidationSchemaRuleBasicCreation:
    """Test basic creation and field constraints."""

    def test_valid_rule_creation_with_defaults(self) -> None:
        """Test creating a valid rule with default values."""
        rule = ModelValidationSchemaRule(
            version=DEFAULT_VERSION,
            key_name="email",
            validation_rule=r"^[\w\.-]+@[\w\.-]+\.\w+$",
        )
        assert rule.key_name == "email"
        assert rule.validation_rule == r"^[\w\.-]+@[\w\.-]+\.\w+$"
        assert rule.rule_type == EnumValidationRuleType.REGEX
        assert rule.error_message is None
        assert rule.is_required is False

    def test_valid_rule_creation_with_custom_values(self) -> None:
        """Test creating a valid rule with all custom values."""
        rule = ModelValidationSchemaRule(
            version=DEFAULT_VERSION,
            key_name="port",
            validation_rule="1..65535",
            rule_type=EnumValidationRuleType.RANGE,
            error_message="Port must be between 1 and 65535",
            is_required=True,
        )
        assert rule.key_name == "port"
        assert rule.validation_rule == "1..65535"
        assert rule.rule_type == EnumValidationRuleType.RANGE
        assert rule.error_message == "Port must be between 1 and 65535"
        assert rule.is_required is True

    def test_required_fields(self) -> None:
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            ModelValidationSchemaRule(version=DEFAULT_VERSION)  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            ModelValidationSchemaRule(version=DEFAULT_VERSION, key_name="test")  # type: ignore[call-arg]

    def test_key_name_min_length(self) -> None:
        """Test that key_name must have minimum length of 1."""
        with pytest.raises(ValidationError) as exc_info:
            ModelValidationSchemaRule(
                version=DEFAULT_VERSION,
                key_name="",  # Empty string not allowed
                validation_rule=".*",
            )
        error_string = str(exc_info.value)
        assert "key_name" in error_string

    def test_validation_rule_min_length(self) -> None:
        """Test that validation_rule must have minimum length of 1."""
        with pytest.raises(ValidationError) as exc_info:
            ModelValidationSchemaRule(
                version=DEFAULT_VERSION,
                key_name="test",
                validation_rule="",  # Empty string not allowed
            )
        error_string = str(exc_info.value)
        assert "validation_rule" in error_string


class TestModelValidationSchemaRuleRegexValidation:
    """Test validation for REGEX rule type."""

    def test_valid_regex_patterns(self) -> None:
        """Test that valid regex patterns are accepted."""
        valid_patterns = [
            r"^[a-z]+$",  # Simple character class
            r"\d{3}-\d{2}-\d{4}",  # SSN pattern
            r"^[\w\.-]+@[\w\.-]+\.\w+$",  # Email pattern
            r"(?:https?://)?(?:www\.)?[a-z0-9]+\.[a-z]{2,}",  # URL pattern
            r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d).{8,}$",  # Password pattern
            r".*",  # Match everything
            r"[^abc]",  # Negated character class
        ]

        for pattern in valid_patterns:
            rule = ModelValidationSchemaRule(
                version=DEFAULT_VERSION,
                key_name="test_field",
                validation_rule=pattern,
                rule_type=EnumValidationRuleType.REGEX,
            )
            assert rule.validation_rule == pattern

    def test_invalid_regex_patterns(self) -> None:
        """Test that invalid regex patterns are rejected."""
        invalid_patterns = [
            r"[",  # Unclosed bracket
            r"(?P<incomplete",  # Incomplete named group
            r"(?P<>invalid)",  # Empty group name
            r"*",  # Nothing to repeat
            r"(?P<name>group)(?P<name>duplicate)",  # Duplicate group name
            r"(?<invalid>python)",  # Invalid lookbehind syntax
        ]

        for pattern in invalid_patterns:
            with pytest.raises(ModelOnexError) as exc_info:
                ModelValidationSchemaRule(
                    version=DEFAULT_VERSION,
                    key_name="test_field",
                    validation_rule=pattern,
                    rule_type=EnumValidationRuleType.REGEX,
                )
            error_string = str(exc_info.value)
            assert "Invalid regex pattern" in error_string
            assert pattern in error_string

    def test_regex_with_special_characters(self) -> None:
        """Test regex patterns with special characters."""
        # These should all be valid
        special_patterns = [
            r"\$\d+\.\d{2}",  # Currency pattern
            r"^\+?1?\d{9,15}$",  # Phone number
            r"[a-zA-Z0-9_\-\.]+",  # Identifier with hyphens
        ]

        for pattern in special_patterns:
            rule = ModelValidationSchemaRule(
                version=DEFAULT_VERSION,
                key_name="test_field",
                validation_rule=pattern,
                rule_type=EnumValidationRuleType.REGEX,
            )
            assert rule.validation_rule == pattern


class TestModelValidationSchemaRuleJSONSchemaValidation:
    """Test validation for JSON_SCHEMA rule type."""

    def test_valid_json_schema_fragments(self) -> None:
        """Test that valid JSON schema fragments are accepted."""
        valid_schemas = [
            '{"type": "string"}',
            '{"type": "number", "minimum": 0}',
            '{"type": "object", "properties": {"name": {"type": "string"}}}',
            '{"type": "array", "items": {"type": "integer"}}',
            '{"enum": ["red", "green", "blue"]}',
            '{"anyOf": [{"type": "string"}, {"type": "number"}]}',
        ]

        for schema in valid_schemas:
            rule = ModelValidationSchemaRule(
                version=DEFAULT_VERSION,
                key_name="test_field",
                validation_rule=schema,
                rule_type=EnumValidationRuleType.JSON_SCHEMA,
            )
            assert rule.validation_rule == schema

    def test_invalid_json_schema_not_object(self) -> None:
        """Test that JSON schema must be an object (dict), not a primitive."""
        invalid_schemas = [
            '"string"',  # String literal
            "123",  # Number
            "true",  # Boolean
            "null",  # Null
            '["array"]',  # Array
        ]

        for schema in invalid_schemas:
            with pytest.raises(ModelOnexError) as exc_info:
                ModelValidationSchemaRule(
                    version=DEFAULT_VERSION,
                    key_name="test_field",
                    validation_rule=schema,
                    rule_type=EnumValidationRuleType.JSON_SCHEMA,
                )
            error_string = str(exc_info.value)
            assert "Invalid JSON schema" in error_string
            assert "must be an object" in error_string

    def test_malformed_json_rejected(self) -> None:
        """Test that malformed JSON is rejected."""
        malformed_jsons = [
            '{"type": "string"',  # Missing closing brace
            '{type: "string"}',  # Unquoted key
            "{'type': 'string'}",  # Single quotes (invalid JSON)
            '{"type": "string",}',  # Trailing comma
            "{,}",  # Invalid syntax
            "not json at all",  # Not JSON
        ]

        for json_str in malformed_jsons:
            with pytest.raises(ModelOnexError) as exc_info:
                ModelValidationSchemaRule(
                    version=DEFAULT_VERSION,
                    key_name="test_field",
                    validation_rule=json_str,
                    rule_type=EnumValidationRuleType.JSON_SCHEMA,
                )
            error_string = str(exc_info.value)
            # Should mention either JSON parsing error or object requirement
            assert "Invalid JSON" in error_string or "JSON schema" in error_string

    def test_complex_json_schema(self) -> None:
        """Test complex nested JSON schema is accepted."""
        complex_schema = """{
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "age": {"type": "integer", "minimum": 0, "maximum": 150},
                "email": {
                    "type": "string",
                    "format": "email"
                },
                "addresses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "street": {"type": "string"},
                            "city": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["name", "email"]
        }"""

        rule = ModelValidationSchemaRule(
            version=DEFAULT_VERSION,
            key_name="user",
            validation_rule=complex_schema,
            rule_type=EnumValidationRuleType.JSON_SCHEMA,
        )
        assert rule.validation_rule == complex_schema


class TestModelValidationSchemaRuleRangeValidation:
    """Test validation for RANGE rule type."""

    def test_valid_range_expressions(self) -> None:
        """Test that valid range expressions are accepted."""
        valid_ranges = [
            "1..10",  # Full range
            "0..100",  # Zero-based range
            "1..",  # Minimum only
            "..100",  # Maximum only
            "0.5..10.5",  # Float range
            "-10..10",  # Negative to positive
            "-100..-50",  # Negative range
        ]

        for range_expr in valid_ranges:
            rule = ModelValidationSchemaRule(
                version=DEFAULT_VERSION,
                key_name="test_field",
                validation_rule=range_expr,
                rule_type=EnumValidationRuleType.RANGE,
            )
            assert rule.validation_rule == range_expr

    def test_invalid_range_missing_separator(self) -> None:
        """Test that ranges without '..' separator are rejected."""
        invalid_ranges = [
            "1-10",  # Wrong separator
            "1,10",  # Comma separator
            "1 10",  # Space separator
            "1to10",  # Text separator
            "10",  # Single value
        ]

        for range_expr in invalid_ranges:
            with pytest.raises(ModelOnexError) as exc_info:
                ModelValidationSchemaRule(
                    version=DEFAULT_VERSION,
                    key_name="test_field",
                    validation_rule=range_expr,
                    rule_type=EnumValidationRuleType.RANGE,
                )
            error_string = str(exc_info.value)
            assert "Invalid range format" in error_string
            assert "must contain '..'" in error_string

    def test_invalid_range_non_numeric(self) -> None:
        """Test that non-numeric range bounds are rejected."""
        invalid_ranges = [
            "abc..10",  # Non-numeric minimum
            "1..xyz",  # Non-numeric maximum
            "foo..bar",  # Both non-numeric
        ]

        for range_expr in invalid_ranges:
            with pytest.raises(ModelOnexError) as exc_info:
                ModelValidationSchemaRule(
                    version=DEFAULT_VERSION,
                    key_name="test_field",
                    validation_rule=range_expr,
                    rule_type=EnumValidationRuleType.RANGE,
                )
            error_string = str(exc_info.value)
            assert "Invalid range format" in error_string
            assert "not numeric" in error_string

    def test_invalid_range_empty_bounds(self) -> None:
        """Test that ranges with no bounds are rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValidationSchemaRule(
                version=DEFAULT_VERSION,
                key_name="test_field",
                validation_rule="..",
                rule_type=EnumValidationRuleType.RANGE,
            )
        error_string = str(exc_info.value)
        assert "Invalid range format" in error_string
        assert "at least one bound" in error_string.lower()

    def test_invalid_range_multiple_separators(self) -> None:
        """Test that ranges with multiple separators are rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValidationSchemaRule(
                version=DEFAULT_VERSION,
                key_name="test_field",
                validation_rule="1..10..20",
                rule_type=EnumValidationRuleType.RANGE,
            )
        error_string = str(exc_info.value)
        assert "Invalid range format" in error_string


class TestModelValidationSchemaRuleEnumValidation:
    """Test validation for ENUM rule type."""

    def test_valid_enum_expressions(self) -> None:
        """Test that valid enum expressions are accepted."""
        valid_enums = [
            "red,green,blue",  # Simple values
            "ACTIVE,INACTIVE,PENDING",  # Uppercase
            "value1,value2,value3",  # With numbers
            "foo",  # Single value
            "a, b, c",  # With spaces (should be stripped)
        ]

        for enum_expr in valid_enums:
            rule = ModelValidationSchemaRule(
                version=DEFAULT_VERSION,
                key_name="test_field",
                validation_rule=enum_expr,
                rule_type=EnumValidationRuleType.ENUM,
            )
            assert rule.validation_rule == enum_expr

    def test_invalid_enum_empty(self) -> None:
        """Test that empty enum lists are rejected."""
        invalid_enums = [
            ",",  # Just separator
            ",,",  # Multiple separators
            " , , ",  # Whitespace only
        ]

        for enum_expr in invalid_enums:
            with pytest.raises(ModelOnexError) as exc_info:
                ModelValidationSchemaRule(
                    version=DEFAULT_VERSION,
                    key_name="test_field",
                    validation_rule=enum_expr,
                    rule_type=EnumValidationRuleType.ENUM,
                )
            error_string = str(exc_info.value)
            assert "Invalid enum format" in error_string
            assert "at least one non-empty value" in error_string

    def test_invalid_enum_duplicates(self) -> None:
        """Test that duplicate enum values are rejected."""
        invalid_enums = [
            "red,green,red",  # Exact duplicate
            "foo,bar,foo",  # Duplicate in different position
            "a,b,c,a,b",  # Multiple duplicates
        ]

        for enum_expr in invalid_enums:
            with pytest.raises(ModelOnexError) as exc_info:
                ModelValidationSchemaRule(
                    version=DEFAULT_VERSION,
                    key_name="test_field",
                    validation_rule=enum_expr,
                    rule_type=EnumValidationRuleType.ENUM,
                )
            error_string = str(exc_info.value)
            assert "Invalid enum format" in error_string
            assert "Duplicate values" in error_string

    def test_enum_whitespace_handling(self) -> None:
        """Test that whitespace is properly handled in enum values."""
        rule = ModelValidationSchemaRule(
            version=DEFAULT_VERSION,
            key_name="test_field",
            validation_rule="  red  ,  green  ,  blue  ",
            rule_type=EnumValidationRuleType.ENUM,
        )
        # Should succeed - whitespace is stripped during validation
        assert rule.validation_rule == "  red  ,  green  ,  blue  "


class TestModelValidationSchemaRuleEdgeCases:
    """Test edge cases and special scenarios."""

    def test_validate_assignment_enabled(self) -> None:
        """Test that validate_assignment is enabled in model config."""
        rule = ModelValidationSchemaRule(
            version=DEFAULT_VERSION,
            key_name="test",
            validation_rule="valid,values",
            rule_type=EnumValidationRuleType.ENUM,
        )

        # Try to assign invalid value after creation
        with pytest.raises(ValidationError):
            rule.validation_rule = ""  # Empty string violates min_length

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields are ignored per model config."""
        rule_data = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "key_name": "test",
            "validation_rule": ".*",
            "custom_field": "custom_value",
            "unknown_setting": 123,
        }

        rule = ModelValidationSchemaRule.model_validate(rule_data)

        assert rule.key_name == "test"
        assert not hasattr(rule, "custom_field")
        assert not hasattr(rule, "unknown_setting")

    def test_model_serialization_round_trip(self) -> None:
        """Test that model can be serialized and deserialized correctly."""
        original = ModelValidationSchemaRule(
            version=DEFAULT_VERSION,
            key_name="email",
            validation_rule=r"^[\w\.-]+@[\w\.-]+\.\w+$",
            rule_type=EnumValidationRuleType.REGEX,
            error_message="Invalid email format",
            is_required=True,
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize back
        restored = ModelValidationSchemaRule.model_validate(data)

        assert restored.key_name == original.key_name
        assert restored.validation_rule == original.validation_rule
        assert restored.rule_type == original.rule_type
        assert restored.error_message == original.error_message
        assert restored.is_required == original.is_required

    def test_different_rule_types_with_same_validation_rule(self) -> None:
        """Test that validation depends on rule_type, not just validation_rule."""
        # Test that comma-separated values fail as RANGE
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValidationSchemaRule(
                version=DEFAULT_VERSION,
                key_name="test",
                validation_rule="red,green,blue",  # Valid enum, invalid range
                rule_type=EnumValidationRuleType.RANGE,
            )
        assert "Invalid range format" in str(exc_info.value)

        # But succeed as ENUM (valid enum values)
        rule = ModelValidationSchemaRule(
            version=DEFAULT_VERSION,
            key_name="test",
            validation_rule="red,green,blue",
            rule_type=EnumValidationRuleType.ENUM,
        )
        assert rule.rule_type == EnumValidationRuleType.ENUM

    def test_rule_type_enum_values_preserved(self) -> None:
        """Test that enum values are preserved (use_enum_values=False)."""
        rule = ModelValidationSchemaRule(
            version=DEFAULT_VERSION,
            key_name="test",
            validation_rule=".*",
            rule_type=EnumValidationRuleType.REGEX,
        )

        # Should be enum instance, not string value
        assert isinstance(rule.rule_type, EnumValidationRuleType)
        assert rule.rule_type == EnumValidationRuleType.REGEX

    def test_all_rule_types_coverage(self) -> None:
        """Test that all rule types can be successfully instantiated."""
        test_cases = [
            (EnumValidationRuleType.REGEX, r"^\d+$"),
            (EnumValidationRuleType.JSON_SCHEMA, '{"type": "string"}'),
            (EnumValidationRuleType.RANGE, "1..100"),
            (EnumValidationRuleType.ENUM, "a,b,c"),
        ]

        for rule_type, validation_rule in test_cases:
            rule = ModelValidationSchemaRule(
                version=DEFAULT_VERSION,
                key_name="test_field",
                validation_rule=validation_rule,
                rule_type=rule_type,
            )
            assert rule.rule_type == rule_type
            assert rule.validation_rule == validation_rule

    def test_cross_type_validation_errors(self) -> None:
        """Test that using wrong format for rule_type raises appropriate errors."""
        # Range format used with REGEX type (invalid regex with "..")
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValidationSchemaRule(
                version=DEFAULT_VERSION,
                key_name="test",
                validation_rule="[",  # Clearly invalid regex
                rule_type=EnumValidationRuleType.REGEX,
            )
        assert "Invalid regex pattern" in str(exc_info.value)

        # Range format used with JSON_SCHEMA type
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValidationSchemaRule(
                version=DEFAULT_VERSION,
                key_name="test",
                validation_rule="1..10",
                rule_type=EnumValidationRuleType.JSON_SCHEMA,
            )
        assert "Invalid JSON schema" in str(exc_info.value)

        # Enum format used with RANGE type
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValidationSchemaRule(
                version=DEFAULT_VERSION,
                key_name="test",
                validation_rule="a,b,c",
                rule_type=EnumValidationRuleType.RANGE,
            )
        assert "Invalid range format" in str(exc_info.value)
