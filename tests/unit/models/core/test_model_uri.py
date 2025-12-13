"""
Unit tests for ModelOnexUri.

Tests all aspects of the ONEX URI model including:
- Model instantiation and validation
- Field validation and type checking
- Literal type validation for 'type' field
- Serialization/deserialization
- Edge cases and error conditions
"""

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from omnibase_core.models.examples.model_uri import ModelOnexUri
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


class TestModelOnexUri:
    """Test cases for ModelOnexUri."""

    def test_model_instantiation_valid_data(self):
        """Test that model can be instantiated with valid data."""
        uri = ModelOnexUri(
            type="tool",
            namespace="python://omnibase.core",
            version_spec=">=1.0.0",
            original="tool://python://omnibase.core@>=1.0.0",
        )

        assert uri.type == "tool"
        assert uri.namespace == "python://omnibase.core"
        assert uri.version_spec == ">=1.0.0"
        assert uri.original == "tool://python://omnibase.core@>=1.0.0"

    def test_model_instantiation_all_valid_types(self):
        """Test model instantiation with all valid literal types."""
        valid_types = [
            "tool",
            "validator",
            "agent",
            "model",
            "plugin",
            "schema",
            "node",
        ]

        for uri_type in valid_types:
            uri = ModelOnexUri(
                type=uri_type,
                namespace="test://namespace",
                version_spec="1.0.0",
                original=f"{uri_type}://test://namespace@1.0.0",
            )
            assert uri.type == uri_type

    def test_required_fields_validation(self):
        """Test that required fields are properly validated."""
        # Missing type
        with pytest.raises(ValidationError) as exc_info:
            ModelOnexUri(
                namespace="test://namespace",
                version_spec="1.0.0",
                original="test://namespace@1.0.0",
            )
        assert "type" in str(exc_info.value)

        # Missing namespace
        with pytest.raises(ValidationError) as exc_info:
            ModelOnexUri(
                type="tool",
                version_spec="1.0.0",
                original="tool://test@1.0.0",
            )
        assert "namespace" in str(exc_info.value)

        # Missing version_spec
        with pytest.raises(ValidationError) as exc_info:
            ModelOnexUri(
                type="tool",
                namespace="test://namespace",
                original="tool://test://namespace",
            )
        assert "version_spec" in str(exc_info.value)

        # Missing original
        with pytest.raises(ValidationError) as exc_info:
            ModelOnexUri(
                type="tool",
                namespace="test://namespace",
                version_spec="1.0.0",
            )
        assert "original" in str(exc_info.value)

    def test_type_literal_validation(self):
        """Test that type field accepts only valid literal values."""
        # Invalid type values
        invalid_types = [
            "invalid",
            "service",
            "component",
            "module",
            "Tool",  # Case sensitive
            "TOOL",  # Case sensitive
            "",
            "test",
        ]

        for invalid_type in invalid_types:
            with pytest.raises(ValidationError) as exc_info:
                ModelOnexUri(
                    type=invalid_type,
                    namespace="test://namespace",
                    version_spec="1.0.0",
                    original=f"{invalid_type}://test://namespace@1.0.0",
                )
            # Should mention literal values or input validation
            error_str = str(exc_info.value).lower()
            assert (
                "literal" in error_str or "input" in error_str or "value" in error_str
            )

    def test_field_types_validation(self):
        """Test that field types are properly validated."""
        # Test non-string type (even if it would be valid literal value)
        with pytest.raises(ValidationError):
            ModelOnexUri(
                type=123,
                namespace="test://namespace",
                version_spec="1.0.0",
                original="tool://test://namespace@1.0.0",
            )

        # Test non-string namespace
        with pytest.raises(ValidationError):
            ModelOnexUri(
                type="tool",
                namespace=123,
                version_spec="1.0.0",
                original="tool://test://namespace@1.0.0",
            )

        # Test non-string version_spec
        with pytest.raises(ValidationError):
            ModelOnexUri(
                type="tool",
                namespace="test://namespace",
                version_spec=123,
                original="tool://test://namespace@1.0.0",
            )

        # Test non-string original
        with pytest.raises(ValidationError):
            ModelOnexUri(
                type="tool",
                namespace="test://namespace",
                version_spec="1.0.0",
                original=123,
            )

    def test_various_namespace_formats(self):
        """Test various valid namespace formats."""
        valid_namespaces = [
            "python://omnibase.core",
            "node://app.component",
            "schema://data.model",
            "tool://utils.helper",
            "validator://checks.compliance",
            "simple_namespace",
            "namespace-with-dashes",
            "namespace_with_underscores",
            "namespace.with.dots",
            "namespace123",
            "a",
            "/path/to/resource",
            "https://example.com/resource",
        ]

        for namespace in valid_namespaces:
            uri = ModelOnexUri(
                type="tool",
                namespace=namespace,
                version_spec="1.0.0",
                original=f"tool://{namespace}@1.0.0",
            )
            assert uri.namespace == namespace

    def test_various_version_specs(self):
        """Test various valid version specifier formats."""
        valid_version_specs = [
            "1.0.0",
            ">=1.0.0",
            "~1.2.3",
            "^2.0.0",
            "1.0.0 - 2.0.0",
            "*",
            "latest",
            ">=1.0.0,<2.0.0",
            "==1.5.3",
            "!=1.4.0",
            "v1.0.0",
            "1.0.0-alpha",
            "1.0.0-beta.1",
            "1.0.0+build.123",
        ]

        for version_spec in valid_version_specs:
            uri = ModelOnexUri(
                type="tool",
                namespace="test://namespace",
                version_spec=version_spec,
                original=f"tool://test://namespace@{version_spec}",
            )
            assert uri.version_spec == version_spec

    def test_original_uri_formats(self):
        """Test various original URI formats."""
        original_uris = [
            "tool://python://omnibase.core@1.0.0",
            "validator://checks.compliance@>=2.0.0",
            "agent://ai.assistant@latest",
            "model://data.schema@~1.5.0",
            "plugin://extension.helper@^3.0.0",
            "schema://api.definition@1.0.0-alpha",
            "node://app.component@*",
            "simple_uri_format",
            "/local/path/to/resource",
            "https://remote.server/resource@1.0.0",
        ]

        for original in original_uris:
            uri = ModelOnexUri(
                type="tool",
                namespace="test://namespace",
                version_spec="1.0.0",
                original=original,
            )
            assert uri.original == original

    def test_real_world_uri_examples(self):
        """Test with realistic ONEX URI examples."""
        # Tool URI
        tool_uri = ModelOnexUri(
            type="tool",
            namespace="python://omnibase.tools.validator",
            version_spec=">=1.2.0",
            original="tool://python://omnibase.tools.validator@>=1.2.0",
        )
        assert tool_uri.type == "tool"
        assert tool_uri.namespace == "python://omnibase.tools.validator"

        # Validator URI
        validator_uri = ModelOnexUri(
            type="validator",
            namespace="contract://compliance.checker",
            version_spec="~2.1.0",
            original="validator://contract://compliance.checker@~2.1.0",
        )
        assert validator_uri.type == "validator"
        assert validator_uri.namespace == "contract://compliance.checker"

        # Agent URI
        agent_uri = ModelOnexUri(
            type="agent",
            namespace="ai://assistant.cognitive",
            version_spec="latest",
            original="agent://ai://assistant.cognitive@latest",
        )
        assert agent_uri.type == "agent"
        assert agent_uri.namespace == "ai://assistant.cognitive"

    def test_model_serialization(self):
        """Test model serialization to dict."""
        uri = ModelOnexUri(
            type="model",
            namespace="data://schema.user",
            version_spec="^1.0.0",
            original="model://data://schema.user@^1.0.0",
        )

        data = uri.model_dump()

        expected_data = {
            "type": "model",
            "namespace": "data://schema.user",
            "version_spec": "^1.0.0",
            "original": "model://data://schema.user@^1.0.0",
        }

        assert data == expected_data

    def test_model_deserialization(self):
        """Test model deserialization from dict."""
        data = {
            "type": "plugin",
            "namespace": "extension://ui.components",
            "version_spec": ">=2.0.0,<3.0.0",
            "original": "plugin://extension://ui.components@>=2.0.0,<3.0.0",
        }

        uri = ModelOnexUri.model_validate(data)

        assert uri.type == "plugin"
        assert uri.namespace == "extension://ui.components"
        assert uri.version_spec == ">=2.0.0,<3.0.0"
        assert uri.original == "plugin://extension://ui.components@>=2.0.0,<3.0.0"

    def test_model_json_serialization(self):
        """Test JSON serialization and deserialization."""
        uri = ModelOnexUri(
            type="schema",
            namespace="api://definitions.rest",
            version_spec="1.0.0",
            original="schema://api://definitions.rest@1.0.0",
        )

        # Serialize to JSON
        json_str = uri.model_dump_json()
        assert isinstance(json_str, str)

        # Deserialize from JSON
        uri_from_json = ModelOnexUri.model_validate_json(json_str)

        assert uri_from_json.type == uri.type
        assert uri_from_json.namespace == uri.namespace
        assert uri_from_json.version_spec == uri.version_spec
        assert uri_from_json.original == uri.original

    def test_model_equality(self):
        """Test model equality comparison."""
        uri1 = ModelOnexUri(
            type="node",
            namespace="app://service.main",
            version_spec="1.0.0",
            original="node://app://service.main@1.0.0",
        )

        uri2 = ModelOnexUri(
            type="node",
            namespace="app://service.main",
            version_spec="1.0.0",
            original="node://app://service.main@1.0.0",
        )

        uri3 = ModelOnexUri(
            type="tool",
            namespace="app://service.main",
            version_spec="1.0.0",
            original="tool://app://service.main@1.0.0",
        )

        assert uri1 == uri2
        assert uri1 != uri3

    def test_model_instantiation_explicit_typing(self):
        """Test that ModelOnexUri uses explicit typing without aliases."""
        # Test direct instantiation
        uri = ModelOnexUri(
            type="tool",
            namespace="test://namespace",
            version_spec="1.0.0",
            original="tool://test://namespace@1.0.0",
        )

        assert isinstance(uri, ModelOnexUri)
        assert uri.type == "tool"


class TestModelOnexUriEdgeCases:
    """Test edge cases and error conditions for ModelOnexUri."""

    def test_empty_string_fields(self):
        """Test behavior with empty string fields."""
        # Empty type should be invalid (not in literal values)
        with pytest.raises(ValidationError):
            ModelOnexUri(
                type="",
                namespace="test://namespace",
                version_spec="1.0.0",
                original="test://namespace@1.0.0",
            )

        # Empty namespace should be valid (no specific constraints)
        uri = ModelOnexUri(
            type="tool",
            namespace="",
            version_spec="1.0.0",
            original="tool://@1.0.0",
        )
        assert uri.namespace == ""

        # Empty version_spec should be valid (no specific constraints)
        uri = ModelOnexUri(
            type="tool",
            namespace="test://namespace",
            version_spec="",
            original="tool://test://namespace@",
        )
        assert uri.version_spec == ""

        # Empty original should be valid (no specific constraints)
        uri = ModelOnexUri(
            type="tool",
            namespace="test://namespace",
            version_spec="1.0.0",
            original="",
        )
        assert uri.original == ""

    def test_whitespace_handling(self):
        """Test handling of whitespace in fields."""
        # Whitespace in type should fail literal validation
        with pytest.raises(ValidationError):
            ModelOnexUri(
                type=" tool ",
                namespace="test://namespace",
                version_spec="1.0.0",
                original="tool://test://namespace@1.0.0",
            )

        # Whitespace in other fields should be preserved
        uri = ModelOnexUri(
            type="tool",
            namespace=" test://namespace ",
            version_spec=" 1.0.0 ",
            original=" tool://test://namespace@1.0.0 ",
        )
        assert uri.namespace == " test://namespace "
        assert uri.version_spec == " 1.0.0 "
        assert uri.original == " tool://test://namespace@1.0.0 "

    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        uri = ModelOnexUri(
            type="tool",
            namespace="tést://namespace_ñ",
            version_spec="1.0.0-émoji🚀",
            original="tool://tést://namespace_ñ@1.0.0-émoji🚀",
        )

        assert "ñ" in uri.namespace
        assert "🚀" in uri.version_spec
        assert "tést" in uri.original

    def test_very_long_strings(self):
        """Test handling of very long strings."""
        long_namespace = "namespace/" + "a" * 10000
        long_version = "1.0.0-" + "b" * 5000
        long_original = "tool://" + "c" * 15000

        uri = ModelOnexUri(
            type="tool",
            namespace=long_namespace,
            version_spec=long_version,
            original=long_original,
        )

        assert len(uri.namespace) > 10000
        assert len(uri.version_spec) > 5000
        assert len(uri.original) > 15000

    def test_special_characters_in_fields(self):
        """Test special characters in allowed fields."""
        special_chars = "!@#$%^&*()[]{}|\\:;\"'<>?,./"

        uri = ModelOnexUri(
            type="tool",
            namespace=f"namespace{special_chars}",
            version_spec=f"1.0.0{special_chars}",
            original=f"tool://namespace{special_chars}@1.0.0{special_chars}",
        )

        assert special_chars in uri.namespace
        assert special_chars in uri.version_spec
        assert special_chars in uri.original

    def test_type_field_edge_cases(self):
        """Test edge cases specifically for the type field."""
        # Test each valid type with edge case namespaces
        valid_types = [
            "tool",
            "validator",
            "agent",
            "model",
            "plugin",
            "schema",
            "node",
        ]

        for uri_type in valid_types:
            # Test with minimal other fields
            uri = ModelOnexUri(
                type=uri_type,
                namespace="a",
                version_spec="1",
                original="x",
            )
            assert uri.type == uri_type

            # Test with complex other fields
            uri = ModelOnexUri(
                type=uri_type,
                namespace="complex://namespace/with/many/parts",
                version_spec=">=1.0.0,<2.0.0,!=1.5.0",
                original=f"{uri_type}://complex://namespace/with/many/parts@>=1.0.0,<2.0.0,!=1.5.0",
            )
            assert uri.type == uri_type

    def test_none_values_not_allowed(self):
        """Test that None values are not allowed for required fields."""
        # All fields are required, so None should not be allowed
        with pytest.raises(ValidationError):
            ModelOnexUri(
                type=None,
                namespace="test://namespace",
                version_spec="1.0.0",
                original="test",
            )

        with pytest.raises(ValidationError):
            ModelOnexUri(
                type="tool",
                namespace=None,
                version_spec="1.0.0",
                original="test",
            )

        with pytest.raises(ValidationError):
            ModelOnexUri(
                type="tool",
                namespace="test://namespace",
                version_spec=None,
                original="test",
            )

        with pytest.raises(ValidationError):
            ModelOnexUri(
                type="tool",
                namespace="test://namespace",
                version_spec="1.0.0",
                original=None,
            )

    def test_mixed_case_type_validation(self):
        """Test that type field is case-sensitive."""
        mixed_case_types = [
            "Tool",
            "TOOL",
            "tOOl",
            "ToOl",
            "Validator",
            "VALIDATOR",
            "vALiDaToR",
            "Agent",
            "AGENT",
            "aGeNt",
            "Model",
            "MODEL",
            "mOdEl",
            "Plugin",
            "PLUGIN",
            "pLuGiN",
            "Schema",
            "SCHEMA",
            "sChEmA",
            "Node",
            "NODE",
            "nOdE",
        ]

        for invalid_case_type in mixed_case_types:
            with pytest.raises(ValidationError):
                ModelOnexUri(
                    type=invalid_case_type,
                    namespace="test://namespace",
                    version_spec="1.0.0",
                    original=f"{invalid_case_type}://test://namespace@1.0.0",
                )

    def test_comprehensive_uri_scenarios(self):
        """Test comprehensive real-world URI scenarios."""
        scenarios = [
            # Development scenarios
            {
                "type": "tool",
                "namespace": "dev://local.development",
                "version_spec": "latest",
                "original": "tool://dev://local.development@latest",
            },
            # Production scenarios
            {
                "type": "validator",
                "namespace": "prod://validation.service",
                "version_spec": "^2.0.0",
                "original": "validator://prod://validation.service@^2.0.0",
            },
            # Testing scenarios
            {
                "type": "agent",
                "namespace": "test://mock.agent",
                "version_spec": ">=1.0.0-alpha",
                "original": "agent://test://mock.agent@>=1.0.0-alpha",
            },
            # Legacy scenarios
            {
                "type": "model",
                "namespace": "legacy://old.system",
                "version_spec": "0.9.0",
                "original": "model://legacy://old.system@0.9.0",
            },
        ]

        for scenario in scenarios:
            uri = ModelOnexUri.model_validate(scenario)
            assert uri.type == scenario["type"]
            assert uri.namespace == scenario["namespace"]
            assert uri.version_spec == scenario["version_spec"]
            assert uri.original == scenario["original"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
