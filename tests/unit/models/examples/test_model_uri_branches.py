"""
Branch coverage tests for ModelOnexUri in examples module.

Tests focus on conditional logic in protocol implementations,
particularly the configure() method's hasattr conditional.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.examples.model_uri import ModelOnexUri


@pytest.mark.unit
class TestModelOnexUriBranchCoverage:
    """Branch coverage tests for ModelOnexUri conditional logic."""

    def test_configure_hasattr_true_branch(self):
        """Test configure when attribute exists (True branch of hasattr)."""
        uri = ModelOnexUri(
            type="tool",
            namespace="test://namespace",
            version_spec="1.0.0",
            original="tool://test://namespace@1.0.0",
        )

        # Configure with existing attributes
        result = uri.configure(
            type="validator", namespace="updated://namespace", version_spec="2.0.0"
        )

        # Should update existing attributes (True branch)
        assert result is True
        assert uri.type == "validator"
        assert uri.namespace == "updated://namespace"
        assert uri.version_spec == "2.0.0"

    def test_configure_hasattr_false_branch(self):
        """Test configure when attribute doesn't exist (False branch of hasattr)."""
        uri = ModelOnexUri(
            type="tool",
            namespace="test://namespace",
            version_spec="1.0.0",
            original="tool://test://namespace@1.0.0",
        )

        # Configure with mix of existing and non-existing attributes
        result = uri.configure(
            type="agent",
            nonexistent_field="should_be_ignored",
            another_invalid_field=123,
        )

        # Should succeed, update existing fields, ignore non-existing (False branch)
        assert result is True
        assert uri.type == "agent"
        assert not hasattr(uri, "nonexistent_field")
        assert not hasattr(uri, "another_invalid_field")

    def test_configure_only_nonexistent_attributes(self):
        """Test configure with only non-existent attributes (all False branches)."""
        uri = ModelOnexUri(
            type="tool",
            namespace="test://namespace",
            version_spec="1.0.0",
            original="tool://test://namespace@1.0.0",
        )

        original_type = uri.type
        original_namespace = uri.namespace

        # Configure with only non-existent attributes
        result = uri.configure(
            invalid_field_1="value1", invalid_field_2="value2", invalid_field_3="value3"
        )

        # Should succeed but make no changes (all False branches)
        assert result is True
        assert uri.type == original_type
        assert uri.namespace == original_namespace
        assert not hasattr(uri, "invalid_field_1")

    def test_configure_empty_kwargs(self):
        """Test configure with no parameters (no loop iterations)."""
        uri = ModelOnexUri(
            type="tool",
            namespace="test://namespace",
            version_spec="1.0.0",
            original="tool://test://namespace@1.0.0",
        )

        # Configure with no parameters
        result = uri.configure()

        # Should succeed with no changes
        assert result is True
        assert uri.type == "tool"
        assert uri.namespace == "test://namespace"

    def test_configure_partial_update(self):
        """Test configure updating only some attributes."""
        uri = ModelOnexUri(
            type="tool",
            namespace="test://namespace",
            version_spec="1.0.0",
            original="tool://test://namespace@1.0.0",
        )

        # Configure updating only namespace
        result = uri.configure(namespace="new://namespace")

        # Should update only specified attribute
        assert result is True
        assert uri.type == "tool"  # Unchanged
        assert uri.namespace == "new://namespace"  # Changed
        assert uri.version_spec == "1.0.0"  # Unchanged

    def test_configure_all_valid_fields(self):
        """Test configure with all valid field updates."""
        uri = ModelOnexUri(
            type="tool",
            namespace="test://namespace",
            version_spec="1.0.0",
            original="tool://test://namespace@1.0.0",
        )

        # Configure updating all fields
        result = uri.configure(
            type="model",
            namespace="updated://namespace",
            version_spec="3.0.0",
            original="model://updated://namespace@3.0.0",
        )

        # Should update all attributes
        assert result is True
        assert uri.type == "model"
        assert uri.namespace == "updated://namespace"
        assert uri.version_spec == "3.0.0"
        assert uri.original == "model://updated://namespace@3.0.0"

    def test_serialize_protocol(self):
        """Test serialize protocol implementation."""
        uri = ModelOnexUri(
            type="plugin",
            namespace="extension://ui.components",
            version_spec=">=2.0.0",
            original="plugin://extension://ui.components@>=2.0.0",
        )

        serialized = uri.serialize()

        # Should return dict with all fields
        assert isinstance(serialized, dict)
        assert serialized["type"] == "plugin"
        assert serialized["namespace"] == "extension://ui.components"
        assert serialized["version_spec"] == ">=2.0.0"
        assert serialized["original"] == "plugin://extension://ui.components@>=2.0.0"

    def test_validate_instance_protocol(self):
        """Test validate_instance protocol implementation."""
        uri = ModelOnexUri(
            type="schema",
            namespace="api://definitions.rest",
            version_spec="1.0.0",
            original="schema://api://definitions.rest@1.0.0",
        )

        result = uri.validate_instance()

        # Base implementation should return True
        assert result is True

    def test_protocol_implementations_chaining(self):
        """Test that protocol methods can be chained successfully."""
        uri = ModelOnexUri(
            type="agent",
            namespace="ai://assistant",
            version_spec="latest",
            original="agent://ai://assistant@latest",
        )

        # Chain protocol method calls
        assert uri.validate_instance() is True
        assert uri.configure(type="validator") is True
        serialized = uri.serialize()
        assert serialized["type"] == "validator"

    def test_configure_type_validation_still_enforced(self):
        """Test that Pydantic validation still applies during configure."""
        uri = ModelOnexUri(
            type="tool",
            namespace="test://namespace",
            version_spec="1.0.0",
            original="tool://test://namespace@1.0.0",
        )

        # Configure with invalid type value (not in Literal)
        # This should trigger Pydantic validation
        with pytest.raises(ValidationError):
            uri.configure(type="invalid_type")

    def test_configure_preserves_model_config(self):
        """Test that configure respects model_config settings."""
        uri = ModelOnexUri(
            type="tool",
            namespace="test://namespace",
            version_spec="1.0.0",
            original="tool://test://namespace@1.0.0",
        )

        # Try to set extra field (should be ignored per model_config)
        result = uri.configure(extra_field="should_be_ignored")

        # Should succeed per configure logic, but extra field should not be set
        assert result is True
        assert not hasattr(uri, "extra_field")


@pytest.mark.unit
class TestModelOnexUriProtocolEdgeCases:
    """Edge case tests for protocol implementations."""

    def test_configure_with_none_values(self):
        """Test configure behavior with None values."""
        uri = ModelOnexUri(
            type="tool",
            namespace="test://namespace",
            version_spec="1.0.0",
            original="tool://test://namespace@1.0.0",
        )

        # Configure with None (should trigger validation error for required fields)
        with pytest.raises(ValidationError):
            uri.configure(type=None)

    def test_serialize_after_configure(self):
        """Test serialize produces correct output after configure."""
        uri = ModelOnexUri(
            type="tool",
            namespace="test://namespace",
            version_spec="1.0.0",
            original="tool://test://namespace@1.0.0",
        )

        uri.configure(type="model", namespace="updated://namespace")
        serialized = uri.serialize()

        # Should reflect configured changes
        assert serialized["type"] == "model"
        assert serialized["namespace"] == "updated://namespace"
        assert serialized["version_spec"] == "1.0.0"  # Unchanged

    def test_validate_instance_always_true(self):
        """Test that validate_instance always returns True."""
        # Test with various valid URIs
        uris = [
            ModelOnexUri(
                type="tool", namespace="a", version_spec="1.0.0", original="x"
            ),
            ModelOnexUri(
                type="agent", namespace="b", version_spec="2.0.0", original="y"
            ),
            ModelOnexUri(
                type="model", namespace="c", version_spec="3.0.0", original="z"
            ),
        ]

        for uri in uris:
            assert uri.validate_instance() is True

    def test_configure_multiple_times(self):
        """Test configure can be called multiple times successfully."""
        uri = ModelOnexUri(
            type="tool",
            namespace="test://namespace",
            version_spec="1.0.0",
            original="tool://test://namespace@1.0.0",
        )

        # First configure
        assert uri.configure(type="agent") is True
        assert uri.type == "agent"

        # Second configure
        assert uri.configure(namespace="new://namespace") is True
        assert uri.namespace == "new://namespace"

        # Third configure
        assert uri.configure(version_spec="2.0.0") is True
        assert uri.version_spec == "2.0.0"

    def test_configure_with_special_characters(self):
        """Test configure with special characters in values."""
        uri = ModelOnexUri(
            type="tool",
            namespace="test://namespace",
            version_spec="1.0.0",
            original="tool://test://namespace@1.0.0",
        )

        # Configure with special characters
        special_namespace = "namespace://with/special!@#$%^&*()chars"
        result = uri.configure(namespace=special_namespace)

        assert result is True
        assert uri.namespace == special_namespace


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
