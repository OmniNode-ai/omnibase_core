"""
Tests for ModelSecuritySubcontract.

Comprehensive tests for security subcontract configuration and validation.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.subcontracts.model_security_subcontract import (
    ModelSecuritySubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class TestModelSecuritySubcontractInitialization:
    """Test ModelSecuritySubcontract initialization."""

    def test_create_default_security_subcontract(self):
        """Test creating security subcontract with default values."""
        security = ModelSecuritySubcontract()
        assert security is not None
        assert isinstance(security, ModelSecuritySubcontract)
        assert security.enable_redaction is True
        assert security.enable_encryption is False
        assert security.enable_audit_logging is True
        assert security.enable_access_control is True
        assert security.enable_input_validation is True
        assert security.enable_output_sanitization is True

    def test_security_subcontract_with_custom_values(self):
        """Test creating security subcontract with custom values."""
        security = ModelSecuritySubcontract(
            enable_redaction=False,
            enable_encryption=True,
            encryption_algorithm="chacha20-poly1305",
            max_field_length=5000,
            sensitive_field_patterns=["api_key", "auth_token"],
        )
        assert security.enable_redaction is False
        assert security.enable_encryption is True
        assert security.encryption_algorithm == "chacha20-poly1305"
        assert security.max_field_length == 5000
        # Patterns should be normalized to lowercase
        assert "api_key" in security.sensitive_field_patterns
        assert "auth_token" in security.sensitive_field_patterns

    def test_security_subcontract_inheritance(self):
        """Test that ModelSecuritySubcontract inherits from BaseModel."""
        from pydantic import BaseModel

        security = ModelSecuritySubcontract()
        assert isinstance(security, BaseModel)

    def test_interface_version_present(self):
        """Test that INTERFACE_VERSION is present and correct."""
        assert hasattr(ModelSecuritySubcontract, "INTERFACE_VERSION")
        assert isinstance(ModelSecuritySubcontract.INTERFACE_VERSION, ModelSemVer)
        assert ModelSecuritySubcontract.INTERFACE_VERSION.major == 1
        assert ModelSecuritySubcontract.INTERFACE_VERSION.minor == 0
        assert ModelSecuritySubcontract.INTERFACE_VERSION.patch == 0


class TestModelSecuritySubcontractPatternValidation:
    """Test sensitive field pattern validation."""

    def test_default_patterns_normalized(self):
        """Test that default patterns are normalized to lowercase."""
        security = ModelSecuritySubcontract()
        patterns = security.sensitive_field_patterns
        assert all(p == p.lower() for p in patterns)
        assert "password" in patterns
        assert "secret" in patterns
        assert "token" in patterns
        assert "key" in patterns
        assert "credential" in patterns

    def test_custom_patterns_normalized(self):
        """Test that custom patterns are normalized to lowercase."""
        security = ModelSecuritySubcontract(
            sensitive_field_patterns=["API_KEY", "Auth_Token", "SECRET_value"]
        )
        assert "api_key" in security.sensitive_field_patterns
        assert "auth_token" in security.sensitive_field_patterns
        assert "secret_value" in security.sensitive_field_patterns

    def test_empty_patterns_with_redaction_disabled(self):
        """Test that empty patterns are allowed when redaction is disabled."""
        # This should work when redaction is disabled
        security = ModelSecuritySubcontract(
            enable_redaction=False,
            sensitive_field_patterns=[],
        )
        assert security.enable_redaction is False
        assert security.sensitive_field_patterns == []

    def test_empty_patterns_with_redaction_enabled_fails(self):
        """Test that empty patterns fail when redaction is enabled."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelSecuritySubcontract(
                enable_redaction=True,
                sensitive_field_patterns=[],
            )
        assert "must be provided" in str(exc_info.value)

    def test_duplicate_patterns_after_normalization(self):
        """Test that duplicate patterns after normalization raise error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelSecuritySubcontract(
                sensitive_field_patterns=["password", "PASSWORD", "Password"]
            )
        assert "duplicate patterns" in str(exc_info.value)

    def test_single_pattern(self):
        """Test that a single pattern is valid."""
        security = ModelSecuritySubcontract(sensitive_field_patterns=["secret"])
        assert security.sensitive_field_patterns == ["secret"]


class TestModelSecuritySubcontractEncryptionValidation:
    """Test encryption configuration validation."""

    def test_encryption_algorithm_aes_256_gcm(self):
        """Test encryption_algorithm accepts aes-256-gcm."""
        security = ModelSecuritySubcontract(encryption_algorithm="aes-256-gcm")
        assert security.encryption_algorithm == "aes-256-gcm"

    def test_encryption_algorithm_aes_128_gcm(self):
        """Test encryption_algorithm accepts aes-128-gcm."""
        security = ModelSecuritySubcontract(encryption_algorithm="aes-128-gcm")
        assert security.encryption_algorithm == "aes-128-gcm"

    def test_encryption_algorithm_chacha20_poly1305(self):
        """Test encryption_algorithm accepts chacha20-poly1305."""
        security = ModelSecuritySubcontract(encryption_algorithm="chacha20-poly1305")
        assert security.encryption_algorithm == "chacha20-poly1305"

    def test_encryption_algorithm_invalid(self):
        """Test encryption_algorithm rejects invalid values."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelSecuritySubcontract(encryption_algorithm="invalid_algorithm")
        assert "must be one of" in str(exc_info.value)

    def test_encryption_at_rest_without_encryption_fails(self):
        """Test that encryption_at_rest requires encryption to be enabled."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelSecuritySubcontract(
                enable_encryption=False,
                enable_encryption_at_rest=True,
            )
        assert "enable_encryption must be True" in str(exc_info.value)

    def test_encryption_at_rest_with_encryption_enabled(self):
        """Test that encryption_at_rest works when encryption is enabled."""
        security = ModelSecuritySubcontract(
            enable_encryption=True,
            enable_encryption_at_rest=True,
        )
        assert security.enable_encryption is True
        assert security.enable_encryption_at_rest is True


class TestModelSecuritySubcontractFieldValidation:
    """Test field constraint validation."""

    def test_max_field_length_minimum(self):
        """Test max_field_length minimum constraint."""
        security = ModelSecuritySubcontract(max_field_length=100)
        assert security.max_field_length == 100

        with pytest.raises(ValidationError):
            ModelSecuritySubcontract(max_field_length=99)

    def test_max_field_length_maximum(self):
        """Test max_field_length maximum constraint."""
        security = ModelSecuritySubcontract(max_field_length=1000000)
        assert security.max_field_length == 1000000

        with pytest.raises(ValidationError):
            ModelSecuritySubcontract(max_field_length=1000001)

    def test_redaction_placeholder_not_empty(self):
        """Test that redaction_placeholder cannot be empty."""
        with pytest.raises(ValidationError):
            ModelSecuritySubcontract(redaction_placeholder="")

    def test_custom_redaction_placeholder(self):
        """Test custom redaction placeholder."""
        security = ModelSecuritySubcontract(redaction_placeholder="***HIDDEN***")
        assert security.redaction_placeholder == "***HIDDEN***"


class TestModelSecuritySubcontractSerialization:
    """Test ModelSecuritySubcontract serialization."""

    def test_security_subcontract_serialization(self):
        """Test security subcontract model_dump."""
        security = ModelSecuritySubcontract(
            enable_encryption=True,
            encryption_algorithm="chacha20-poly1305",
            max_field_length=5000,
        )
        data = security.model_dump()
        assert isinstance(data, dict)
        assert data["enable_encryption"] is True
        assert data["encryption_algorithm"] == "chacha20-poly1305"
        assert data["max_field_length"] == 5000

    def test_security_subcontract_deserialization(self):
        """Test security subcontract model_validate."""
        data = {
            "enable_redaction": False,
            "enable_encryption": True,
            "encryption_algorithm": "aes-128-gcm",
            "sensitive_field_patterns": ["api_key"],
        }
        security = ModelSecuritySubcontract.model_validate(data)
        assert security.enable_redaction is False
        assert security.enable_encryption is True
        assert security.encryption_algorithm == "aes-128-gcm"
        assert "api_key" in security.sensitive_field_patterns

    def test_security_subcontract_json_serialization(self):
        """Test security subcontract JSON serialization."""
        security = ModelSecuritySubcontract()
        json_data = security.model_dump_json()
        assert isinstance(json_data, str)
        assert "enable_redaction" in json_data
        assert "sensitive_field_patterns" in json_data

    def test_security_subcontract_roundtrip(self):
        """Test serialization and deserialization roundtrip."""
        original = ModelSecuritySubcontract(
            enable_redaction=True,
            sensitive_field_patterns=["custom_secret"],
            enable_encryption=True,
            encryption_algorithm="chacha20-poly1305",
            max_field_length=8000,
        )
        data = original.model_dump()
        restored = ModelSecuritySubcontract.model_validate(data)
        assert restored.enable_redaction == original.enable_redaction
        assert restored.sensitive_field_patterns == original.sensitive_field_patterns
        assert restored.enable_encryption == original.enable_encryption
        assert restored.encryption_algorithm == original.encryption_algorithm
        assert restored.max_field_length == original.max_field_length


class TestModelSecuritySubcontractAuditLogging:
    """Test audit logging configuration."""

    def test_all_audit_features_enabled(self):
        """Test enabling all audit features."""
        security = ModelSecuritySubcontract(
            enable_audit_logging=True,
            audit_sensitive_operations=True,
            audit_access_attempts=True,
        )
        assert security.enable_audit_logging is True
        assert security.audit_sensitive_operations is True
        assert security.audit_access_attempts is True

    def test_audit_logging_disabled(self):
        """Test disabling audit logging."""
        security = ModelSecuritySubcontract(
            enable_audit_logging=False,
            audit_sensitive_operations=False,
            audit_access_attempts=False,
        )
        assert security.enable_audit_logging is False
        assert security.audit_sensitive_operations is False
        assert security.audit_access_attempts is False


class TestModelSecuritySubcontractAccessControl:
    """Test access control configuration."""

    def test_all_access_control_enabled(self):
        """Test enabling all access control features."""
        security = ModelSecuritySubcontract(
            enable_access_control=True,
            require_authentication=True,
            require_authorization=True,
        )
        assert security.enable_access_control is True
        assert security.require_authentication is True
        assert security.require_authorization is True

    def test_access_control_disabled(self):
        """Test disabling access control."""
        security = ModelSecuritySubcontract(
            enable_access_control=False,
            require_authentication=False,
            require_authorization=False,
        )
        assert security.enable_access_control is False
        assert security.require_authentication is False
        assert security.require_authorization is False


class TestModelSecuritySubcontractInputValidation:
    """Test input validation configuration."""

    def test_all_input_validation_enabled(self):
        """Test enabling all input validation features."""
        security = ModelSecuritySubcontract(
            enable_input_validation=True,
            enable_sql_injection_protection=True,
            enable_xss_protection=True,
        )
        assert security.enable_input_validation is True
        assert security.enable_sql_injection_protection is True
        assert security.enable_xss_protection is True

    def test_input_validation_disabled(self):
        """Test disabling input validation."""
        security = ModelSecuritySubcontract(
            enable_input_validation=False,
            enable_sql_injection_protection=False,
            enable_xss_protection=False,
        )
        assert security.enable_input_validation is False
        assert security.enable_sql_injection_protection is False
        assert security.enable_xss_protection is False


class TestModelSecuritySubcontractOutputSanitization:
    """Test output sanitization configuration."""

    def test_all_sanitization_enabled(self):
        """Test enabling all output sanitization features."""
        security = ModelSecuritySubcontract(
            enable_output_sanitization=True,
            sanitize_html=True,
            sanitize_scripts=True,
        )
        assert security.enable_output_sanitization is True
        assert security.sanitize_html is True
        assert security.sanitize_scripts is True

    def test_sanitization_disabled(self):
        """Test disabling output sanitization."""
        security = ModelSecuritySubcontract(
            enable_output_sanitization=False,
            sanitize_html=False,
            sanitize_scripts=False,
        )
        assert security.enable_output_sanitization is False
        assert security.sanitize_html is False
        assert security.sanitize_scripts is False


class TestModelSecuritySubcontractSecurityPolicies:
    """Test security policy configuration."""

    def test_all_security_policies_enabled(self):
        """Test enabling all security policies."""
        security = ModelSecuritySubcontract(
            enforce_https=True,
            enable_rate_limiting=True,
            enable_csrf_protection=True,
        )
        assert security.enforce_https is True
        assert security.enable_rate_limiting is True
        assert security.enable_csrf_protection is True

    def test_security_policies_disabled(self):
        """Test disabling security policies."""
        security = ModelSecuritySubcontract(
            enforce_https=False,
            enable_rate_limiting=False,
            enable_csrf_protection=False,
        )
        assert security.enforce_https is False
        assert security.enable_rate_limiting is False
        assert security.enable_csrf_protection is False


class TestModelSecuritySubcontractEdgeCases:
    """Test security subcontract edge cases."""

    def test_minimal_security_configuration(self):
        """Test minimal security configuration."""
        security = ModelSecuritySubcontract(
            enable_redaction=False,
            enable_encryption=False,
            enable_audit_logging=False,
            enable_access_control=False,
            enable_input_validation=False,
            enable_output_sanitization=False,
            sensitive_field_patterns=[],  # Empty when redaction disabled
        )
        assert security.enable_redaction is False
        assert security.enable_encryption is False
        assert security.enable_audit_logging is False

    def test_maximal_security_configuration(self):
        """Test maximal security configuration."""
        security = ModelSecuritySubcontract(
            enable_redaction=True,
            enable_encryption=True,
            enable_encryption_at_rest=True,
            enable_audit_logging=True,
            audit_sensitive_operations=True,
            audit_access_attempts=True,
            enable_access_control=True,
            require_authentication=True,
            require_authorization=True,
            enable_input_validation=True,
            enable_sql_injection_protection=True,
            enable_xss_protection=True,
            enable_output_sanitization=True,
            sanitize_html=True,
            sanitize_scripts=True,
            enforce_https=True,
            enable_rate_limiting=True,
            enable_csrf_protection=True,
        )
        assert security.enable_redaction is True
        assert security.enable_encryption is True
        assert security.enable_encryption_at_rest is True


class TestModelSecuritySubcontractAttributes:
    """Test security subcontract attributes and metadata."""

    def test_security_subcontract_attributes(self):
        """Test that security subcontract has expected attributes."""
        security = ModelSecuritySubcontract()
        assert hasattr(security, "model_dump")
        assert callable(security.model_dump)
        assert hasattr(ModelSecuritySubcontract, "model_validate")
        assert callable(ModelSecuritySubcontract.model_validate)

    def test_security_subcontract_docstring(self):
        """Test security subcontract docstring."""
        assert ModelSecuritySubcontract.__doc__ is not None
        assert "security" in ModelSecuritySubcontract.__doc__.lower()

    def test_security_subcontract_class_name(self):
        """Test security subcontract class name."""
        assert ModelSecuritySubcontract.__name__ == "ModelSecuritySubcontract"

    def test_security_subcontract_module(self):
        """Test security subcontract module."""
        assert (
            ModelSecuritySubcontract.__module__
            == "omnibase_core.models.contracts.subcontracts.model_security_subcontract"
        )

    def test_security_subcontract_copy(self):
        """Test security subcontract copying."""
        security = ModelSecuritySubcontract(max_field_length=5000)
        copied = security.model_copy()
        assert copied is not None
        assert copied.max_field_length == 5000
        assert copied is not security


class TestModelSecuritySubcontractConfigDict:
    """Test security subcontract ConfigDict settings."""

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored."""
        data = {
            "enable_redaction": True,
            "extra_field": "should_be_ignored",
            "another_extra": 123,
        }
        security = ModelSecuritySubcontract.model_validate(data)
        assert security.enable_redaction is True
        assert not hasattr(security, "extra_field")
        assert not hasattr(security, "another_extra")

    def test_validate_assignment_enabled(self):
        """Test that assignment validation is enabled."""
        security = ModelSecuritySubcontract()

        # This should trigger validation
        with pytest.raises(ValidationError):
            security.max_field_length = 50  # Below minimum of 100
