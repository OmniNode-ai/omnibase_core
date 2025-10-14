"""
Unit tests for EnumAuthType.

Tests all aspects of the authentication type enum including:
- Enum value validation
- Helper methods and class methods
- String representation
- JSON serialization compatibility
- Pydantic integration
- Security-related categorization logic
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_auth_type import EnumAuthType


class TestEnumAuthType:
    """Test cases for EnumAuthType."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "NONE": "none",
            "BASIC": "basic",
            "BEARER": "bearer",
            "OAUTH2": "oauth2",
            "JWT": "jwt",
            "API_KEY": "api_key",
            "API_KEY_HEADER": "api_key_header",
            "MTLS": "mtls",
            "DIGEST": "digest",
            "CUSTOM": "custom",
        }

        for name, value in expected_values.items():
            auth_type = getattr(EnumAuthType, name)
            assert auth_type.value == value
            assert str(auth_type) == value

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(EnumAuthType.NONE) == "none"
        assert str(EnumAuthType.BEARER) == "bearer"
        assert str(EnumAuthType.OAUTH2) == "oauth2"
        assert str(EnumAuthType.JWT) == "jwt"

    def test_requires_credentials(self):
        """Test the requires_credentials class method."""
        # Auth types that don't require credentials
        assert EnumAuthType.requires_credentials(EnumAuthType.NONE) is False

        # Auth types that require credentials
        credential_types = [
            EnumAuthType.BASIC,
            EnumAuthType.BEARER,
            EnumAuthType.OAUTH2,
            EnumAuthType.JWT,
            EnumAuthType.API_KEY,
            EnumAuthType.API_KEY_HEADER,
            EnumAuthType.MTLS,
            EnumAuthType.DIGEST,
            EnumAuthType.CUSTOM,
        ]

        for auth_type in credential_types:
            assert EnumAuthType.requires_credentials(auth_type) is True

    def test_is_token_based(self):
        """Test the is_token_based class method."""
        # Token-based auth types
        token_types = [
            EnumAuthType.BEARER,
            EnumAuthType.OAUTH2,
            EnumAuthType.JWT,
            EnumAuthType.API_KEY,
            EnumAuthType.API_KEY_HEADER,
        ]

        for auth_type in token_types:
            assert EnumAuthType.is_token_based(auth_type) is True

        # Non-token-based auth types
        non_token_types = [
            EnumAuthType.NONE,
            EnumAuthType.BASIC,
            EnumAuthType.MTLS,
            EnumAuthType.DIGEST,
            EnumAuthType.CUSTOM,
        ]

        for auth_type in non_token_types:
            assert EnumAuthType.is_token_based(auth_type) is False

    def test_is_certificate_based(self):
        """Test the is_certificate_based class method."""
        # Certificate-based auth types
        assert EnumAuthType.is_certificate_based(EnumAuthType.MTLS) is True

        # Non-certificate-based auth types
        non_cert_types = [
            EnumAuthType.NONE,
            EnumAuthType.BASIC,
            EnumAuthType.BEARER,
            EnumAuthType.OAUTH2,
            EnumAuthType.JWT,
            EnumAuthType.API_KEY,
            EnumAuthType.API_KEY_HEADER,
            EnumAuthType.DIGEST,
            EnumAuthType.CUSTOM,
        ]

        for auth_type in non_cert_types:
            assert EnumAuthType.is_certificate_based(auth_type) is False

    def test_supports_refresh(self):
        """Test the supports_refresh class method."""
        # Auth types that support refresh
        refresh_types = [
            EnumAuthType.OAUTH2,
            EnumAuthType.JWT,
        ]

        for auth_type in refresh_types:
            assert EnumAuthType.supports_refresh(auth_type) is True

        # Auth types that don't support refresh
        non_refresh_types = [
            EnumAuthType.NONE,
            EnumAuthType.BASIC,
            EnumAuthType.BEARER,
            EnumAuthType.API_KEY,
            EnumAuthType.API_KEY_HEADER,
            EnumAuthType.MTLS,
            EnumAuthType.DIGEST,
            EnumAuthType.CUSTOM,
        ]

        for auth_type in non_refresh_types:
            assert EnumAuthType.supports_refresh(auth_type) is False

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumAuthType.OAUTH2 == EnumAuthType.OAUTH2
        assert EnumAuthType.BASIC != EnumAuthType.BEARER
        assert EnumAuthType.JWT == EnumAuthType.JWT

    def test_enum_membership(self):
        """Test enum membership checking."""
        all_auth_types = [
            EnumAuthType.NONE,
            EnumAuthType.BASIC,
            EnumAuthType.BEARER,
            EnumAuthType.OAUTH2,
            EnumAuthType.JWT,
            EnumAuthType.API_KEY,
            EnumAuthType.API_KEY_HEADER,
            EnumAuthType.MTLS,
            EnumAuthType.DIGEST,
            EnumAuthType.CUSTOM,
        ]

        for auth_type in all_auth_types:
            assert auth_type in EnumAuthType

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        auth_types = list(EnumAuthType)
        assert len(auth_types) == 10

        auth_values = [auth.value for auth in auth_types]
        expected_values = [
            "none",
            "basic",
            "bearer",
            "oauth2",
            "jwt",
            "api_key",
            "api_key_header",
            "mtls",
            "digest",
            "custom",
        ]

        assert set(auth_values) == set(expected_values)

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Test direct serialization
        auth_type = EnumAuthType.OAUTH2
        json_str = json.dumps(auth_type, default=str)
        assert json_str == '"oauth2"'

        # Test in dictionary
        data = {"auth_type": EnumAuthType.JWT}
        json_str = json.dumps(data, default=str)
        assert '"auth_type": "jwt"' in json_str

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class EnumAuthConfig(BaseModel):
            auth_type: EnumAuthType

        # Test valid enum assignment
        config = EnumAuthConfig(auth_type=EnumAuthType.BEARER)
        assert config.auth_type == EnumAuthType.BEARER

        # Test string assignment (should work due to str inheritance)
        config = EnumAuthConfig(auth_type="oauth2")
        assert config.auth_type == EnumAuthType.OAUTH2

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            EnumAuthConfig(auth_type="invalid_auth_type")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class EnumAuthConfig(BaseModel):
            auth_type: EnumAuthType

        config = EnumAuthConfig(auth_type=EnumAuthType.JWT)

        # Test dict serialization
        config_dict = config.model_dump()
        assert config_dict == {"auth_type": "jwt"}

        # Test JSON serialization
        json_str = config.model_dump_json()
        assert json_str == '{"auth_type":"jwt"}'

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Test case sensitivity (should be case-sensitive)
        assert EnumAuthType.OAUTH2.value == "oauth2"
        assert EnumAuthType.OAUTH2.value != "OAUTH2"
        assert EnumAuthType.OAUTH2.value != "OAuth2"

        # Test that we can't create invalid enum values
        with pytest.raises((ValueError, AttributeError)):
            _ = EnumAuthType("invalid_value")

    def test_comprehensive_security_classification(self):
        """Test comprehensive security-related classifications."""
        # High security auth types (strong authentication)
        high_security_types = [
            EnumAuthType.MTLS,  # Certificate-based
            EnumAuthType.OAUTH2,  # Token-based with refresh
            EnumAuthType.JWT,  # Token-based with refresh
        ]

        for auth_type in high_security_types:
            assert EnumAuthType.requires_credentials(auth_type) is True
            # Either token-based or certificate-based (high security)
            assert (
                EnumAuthType.is_token_based(auth_type)
                or EnumAuthType.is_certificate_based(auth_type)
            ) is True

        # Basic security auth types
        basic_security_types = [
            EnumAuthType.BASIC,
            EnumAuthType.BEARER,
            EnumAuthType.API_KEY,
            EnumAuthType.API_KEY_HEADER,
            EnumAuthType.DIGEST,
        ]

        for auth_type in basic_security_types:
            assert EnumAuthType.requires_credentials(auth_type) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
