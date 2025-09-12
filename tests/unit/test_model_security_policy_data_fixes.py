"""
Test suite for ModelSecurityPolicyData critical fixes.

Tests the Priority 1 fixes:
1. Correct method calls (to_python_dict vs to_dict)
2. Proper type annotations (no Any types)
3. Integration with ModelTypedMapping
"""

from typing import get_type_hints

import pytest

from omnibase_core.model.common.model_typed_value import ModelTypedMapping
from omnibase_core.model.security.model_security_policy_data import (
    ModelSecurityPolicyData,
)


class TestModelSecurityPolicyDataMethodFixes:
    """Test suite for method call fixes."""

    def test_data_property_method_call(self):
        """Test that data property calls the correct method."""
        # Create policy data with typed values
        policy = ModelSecurityPolicyData()
        policy.set_policy_value("max_connections", 100)
        policy.set_policy_value("timeout_seconds", 30.0)
        policy.set_policy_value("debug_enabled", False)
        policy.set_policy_value("allowed_hosts", ["localhost", "example.com"])

        # Call the data property - should not raise AttributeError
        data_dict = policy.data

        # Verify we get the expected dictionary
        assert isinstance(data_dict, dict)
        assert data_dict["max_connections"] == 100
        assert data_dict["timeout_seconds"] == 30.0
        assert data_dict["debug_enabled"] is False
        assert data_dict["allowed_hosts"] == ["localhost", "example.com"]

    def test_from_dict_method_call(self):
        """Test that from_dict calls the correct method."""
        test_data = {
            "api_version": "v2",
            "rate_limit": 1000,
            "ssl_enabled": True,
            "endpoints": ["/api/v1", "/api/v2"],
            "config": {"cache_size": 512, "log_level": "INFO"},
        }

        # This should not raise AttributeError
        policy = ModelSecurityPolicyData.from_dict(test_data)

        # Verify the data was properly converted
        assert isinstance(policy, ModelSecurityPolicyData)
        assert policy.get_policy_value("api_version") == "v2"
        assert policy.get_policy_value("rate_limit") == 1000
        assert policy.get_policy_value("ssl_enabled") is True
        assert policy.get_policy_value("endpoints") == ["/api/v1", "/api/v2"]
        assert policy.get_policy_value("config") == {
            "cache_size": 512,
            "log_level": "INFO",
        }

    def test_round_trip_data_conversion(self):
        """Test round-trip conversion from dict to policy to dict."""
        original_data = {
            "security_level": "high",
            "max_attempts": 3,
            "lockout_duration": 300.5,
            "two_factor_required": True,
            "allowed_methods": ["GET", "POST"],
            "permissions": {"read": True, "write": False},
        }

        # Convert to policy and back
        policy = ModelSecurityPolicyData.from_dict(original_data)
        converted_data = policy.data

        # Should match original data
        assert converted_data["security_level"] == original_data["security_level"]
        assert converted_data["max_attempts"] == original_data["max_attempts"]
        assert converted_data["lockout_duration"] == original_data["lockout_duration"]
        assert (
            converted_data["two_factor_required"]
            == original_data["two_factor_required"]
        )
        assert converted_data["allowed_methods"] == original_data["allowed_methods"]
        assert converted_data["permissions"] == original_data["permissions"]


class TestModelSecurityPolicyDataTypeAnnotations:
    """Test suite for type annotations and Any type elimination."""

    def test_data_property_return_type(self):
        """Test that data property has proper type annotations."""
        policy = ModelSecurityPolicyData()
        data = policy.data

        # The return type should be a dict with specific types, not Any
        assert isinstance(data, dict)

        # Verify type hints don't include Any
        type_hints = get_type_hints(ModelSecurityPolicyData.data.fget)
        return_type = type_hints.get("return", None)

        # Should be Union of specific types, not Any
        assert str(return_type) != "typing.Any"
        assert "Any" not in str(return_type)

    def test_set_policy_value_type_annotations(self):
        """Test set_policy_value method type annotations."""
        policy = ModelSecurityPolicyData()

        # Should accept all the specified types without Any
        policy.set_policy_value("string", "value")
        policy.set_policy_value("integer", 42)
        policy.set_policy_value("float", 3.14)
        policy.set_policy_value("boolean", True)
        policy.set_policy_value("list", [1, 2, 3])
        policy.set_policy_value("dict", {"key": "value"})
        policy.set_policy_value("none", None)

        # Verify type hints
        type_hints = get_type_hints(policy.set_policy_value)
        value_type = type_hints.get("value", None)

        # Should not be Any type
        assert "Any" not in str(value_type)

    def test_get_policy_value_type_annotations(self):
        """Test get_policy_value method type annotations."""
        policy = ModelSecurityPolicyData()
        policy.set_policy_value("test_key", "test_value")

        # Should return properly typed value
        value = policy.get_policy_value("test_key")
        assert value == "test_value"

        # Should handle defaults properly
        default_value = policy.get_policy_value("missing_key", "default")
        assert default_value == "default"

        # Verify type hints
        type_hints = get_type_hints(policy.get_policy_value)
        return_type = type_hints.get("return", None)
        default_type = type_hints.get("default", None)

        # Should not be Any types
        assert "Any" not in str(return_type)
        assert "Any" not in str(default_type) if default_type else True

    def test_from_dict_type_annotations(self):
        """Test from_dict method type annotations."""
        test_data = {"key": "value", "number": 123}
        policy = ModelSecurityPolicyData.from_dict(test_data)

        assert isinstance(policy, ModelSecurityPolicyData)

        # Verify type hints
        type_hints = get_type_hints(ModelSecurityPolicyData.from_dict)
        data_type = type_hints.get("data", None)

        # Should not be Any type
        assert "Any" not in str(data_type)


class TestModelSecurityPolicyDataIntegration:
    """Test integration with ModelTypedMapping and edge cases."""

    def test_typed_mapping_integration(self):
        """Test proper integration with ModelTypedMapping."""
        policy = ModelSecurityPolicyData()

        # Verify that typed_data is ModelTypedMapping
        assert isinstance(policy.typed_data, ModelTypedMapping)

        # Test direct access to typed mapping features
        policy.typed_data.set_string("auth_method", "jwt")
        policy.typed_data.set_int("session_timeout", 3600)

        # Should be accessible via policy methods
        assert policy.get_policy_value("auth_method") == "jwt"
        assert policy.get_policy_value("session_timeout") == 3600

        # Should be in data property output
        data = policy.data
        assert data["auth_method"] == "jwt"
        assert data["session_timeout"] == 3600

    def test_complex_nested_policy_data(self):
        """Test handling of complex nested policy structures."""
        complex_policy_data = {
            "authentication": {
                "methods": ["password", "oauth", "saml"],
                "oauth_providers": {
                    "google": {"client_id": "google_client", "enabled": True},
                    "github": {"client_id": "github_client", "enabled": False},
                },
            },
            "authorization": {
                "roles": ["admin", "user", "guest"],
                "permissions": {
                    "admin": ["read", "write", "delete"],
                    "user": ["read", "write"],
                    "guest": ["read"],
                },
            },
            "rate_limiting": {
                "enabled": True,
                "requests_per_minute": 100,
                "burst_limit": 200,
            },
        }

        # Should handle complex nesting within depth limits
        policy = ModelSecurityPolicyData.from_dict(complex_policy_data)

        # Verify nested data is accessible
        auth_data = policy.get_policy_value("authentication")
        assert isinstance(auth_data, dict)
        assert "methods" in auth_data
        assert "oauth_providers" in auth_data

        # Test round-trip
        reconstructed = policy.data
        assert reconstructed["authentication"]["methods"] == [
            "password",
            "oauth",
            "saml",
        ]
        assert reconstructed["rate_limiting"]["enabled"] is True
        assert reconstructed["rate_limiting"]["requests_per_minute"] == 100

    def test_security_policy_edge_cases(self):
        """Test edge cases in security policy handling."""
        # Empty policy
        empty_policy = ModelSecurityPolicyData()
        assert empty_policy.data == {}

        # Policy with None values
        policy_with_none = ModelSecurityPolicyData.from_dict(
            {
                "enabled": True,
                "disabled_feature": None,  # Should be skipped
                "config": {"setting1": "value1", "setting2": None},  # Should be skipped
            }
        )

        data = policy_with_none.data
        assert data["enabled"] is True
        assert "disabled_feature" not in data
        assert isinstance(data["config"], dict)
        # Note: depending on implementation, None handling may vary

    def test_policy_value_type_preservation(self):
        """Test that policy values preserve their types correctly."""
        policy = ModelSecurityPolicyData()

        # Set various types
        policy.set_policy_value("string_val", "test")
        policy.set_policy_value("int_val", 42)
        policy.set_policy_value("float_val", 3.14159)
        policy.set_policy_value("bool_true", True)
        policy.set_policy_value("bool_false", False)
        policy.set_policy_value("list_val", [1, "two", 3.0])
        policy.set_policy_value("dict_val", {"nested": "value"})

        # Verify types are preserved
        assert isinstance(policy.get_policy_value("string_val"), str)
        assert isinstance(policy.get_policy_value("int_val"), int)
        assert isinstance(policy.get_policy_value("float_val"), float)
        assert isinstance(policy.get_policy_value("bool_true"), bool)
        assert isinstance(policy.get_policy_value("bool_false"), bool)
        assert isinstance(policy.get_policy_value("list_val"), list)
        assert isinstance(policy.get_policy_value("dict_val"), dict)

        # Verify exact values
        assert policy.get_policy_value("bool_true") is True
        assert policy.get_policy_value("bool_false") is False
        assert policy.get_policy_value("int_val") == 42
        assert policy.get_policy_value("float_val") == 3.14159


class TestSecurityPolicyDataFeatures:
    """Test security policy data features."""

    def test_property_accessor_patterns(self):
        """Test that property accessors work properly."""
        # Create policy using old-style dict
        legacy_data = {"version": "1.0", "debug": False, "max_users": 1000}

        policy = ModelSecurityPolicyData.from_dict(legacy_data)

        # Old-style access via .data property should still work
        data = policy.data
        assert data.get("version") == "1.0"
        assert data.get("debug") is False
        assert data.get("max_users") == 1000

        # New-style access should also work
        assert policy.get_policy_value("version") == "1.0"
        assert policy.get_policy_value("debug") is False
        assert policy.get_policy_value("max_users") == 1000

    def test_mixed_access_patterns(self):
        """Test mixing old and new access patterns."""
        policy = ModelSecurityPolicyData.from_dict({"initial": "value"})

        # Mix new-style setting with old-style access
        policy.set_policy_value("new_key", "new_value")

        data = policy.data
        assert data["initial"] == "value"
        assert data["new_key"] == "new_value"

        # Mix old-style creation with new-style access
        policy2 = ModelSecurityPolicyData()
        policy2.set_policy_value("mixed", True)

        assert policy2.get_policy_value("mixed") is True
        assert policy2.data["mixed"] is True


if __name__ == "__main__":
    # Run the tests if executed directly
    pytest.main([__file__, "-v"])
