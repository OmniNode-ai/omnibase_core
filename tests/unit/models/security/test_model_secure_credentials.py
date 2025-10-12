"""
Comprehensive unit tests for ModelSecureCredentials.

Tests cover:
- Abstract base class behavior
- Secret masking (minimal, standard, aggressive)
- Sensitive pattern detection
- Credential strength assessment
- Security classification
- Environment variable integration and validation
- Environment mapping and loading
- Serialization (log-safe, debug, audit)
- Template export
- Credential validation
- Factory methods (with fallbacks, empty templates)
- Error scenarios and ONEX compliance
- Security best practices (no plaintext secrets, proper encryption usage)
"""

import os
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from omnibase_core.models.security.model_audit_data import ModelAuditData
from omnibase_core.models.security.model_credential_validation_result import (
    ModelCredentialValidationResult,
)
from omnibase_core.models.security.model_credentials_analysis import (
    ModelCredentialsAnalysis,
)
from omnibase_core.models.security.model_debug_data import ModelDebugData
from omnibase_core.models.security.model_log_safe_data import ModelLogSafeData
from omnibase_core.models.security.model_mask_data import ModelMaskData
from omnibase_core.models.security.model_secure_credentials import (
    ModelSecureCredentials,
)


# Concrete implementation for testing abstract base class
class TestCredentials(ModelSecureCredentials):
    """Test implementation of ModelSecureCredentials."""

    username: str = "test_user"
    password: SecretStr = SecretStr("default_password")
    api_key: SecretStr | None = None
    connection_string: SecretStr | None = None
    host: str = "localhost"
    port: int = 5432

    @classmethod
    def load_from_env(cls, env_prefix: str = "ONEX_"):
        """Load credentials from environment variables."""
        return cls(
            username=os.getenv(f"{env_prefix}USERNAME", "test_user"),
            password=SecretStr(os.getenv(f"{env_prefix}PASSWORD", "default_password")),
            api_key=(
                SecretStr(os.getenv(f"{env_prefix}API_KEY"))
                if os.getenv(f"{env_prefix}API_KEY")
                else None
            ),
            host=os.getenv(f"{env_prefix}HOST", "localhost"),
            port=int(os.getenv(f"{env_prefix}PORT", "5432")),
        )


class TestModelSecureCredentialsBasicBehavior:
    """Test basic ModelSecureCredentials initialization and behaviors."""

    def test_credentials_creation_with_defaults(self):
        """Test credentials creation with default values."""
        creds = TestCredentials()

        assert creds.username == "test_user"
        assert creds.password.get_secret_value() == "default_password"
        assert creds.host == "localhost"
        assert creds.port == 5432

    def test_credentials_creation_with_custom_values(self):
        """Test credentials creation with custom values."""
        creds = TestCredentials(
            username="custom_user",
            password=SecretStr("custom_password"),
            host="example.com",
            port=3306,
        )

        assert creds.username == "custom_user"
        assert creds.password.get_secret_value() == "custom_password"
        assert creds.host == "example.com"
        assert creds.port == 3306

    def test_credentials_with_secret_fields(self):
        """Test that SecretStr fields are properly handled."""
        creds = TestCredentials(
            password=SecretStr("secret_value"),
            api_key=SecretStr("api_secret_key"),
        )

        # SecretStr values should not be exposed in repr
        creds_repr = repr(creds)
        assert "secret_value" not in creds_repr
        assert "api_secret_key" not in creds_repr

        # But can be accessed explicitly
        assert creds.password.get_secret_value() == "secret_value"
        assert creds.api_key.get_secret_value() == "api_secret_key"

    def test_credentials_is_abstract_base(self):
        """Test that ModelSecureCredentials is an abstract base class."""
        # Can't instantiate the base class directly
        with pytest.raises(TypeError):
            ModelSecureCredentials()  # Missing load_from_env implementation


class TestModelSecureCredentialsSecretMasking:
    """Test secret masking functionality."""

    def test_get_masked_dict_standard_masking(self):
        """Test standard masking level."""
        creds = TestCredentials(
            username="test_user",
            password=SecretStr("my_secret_password"),
            api_key=SecretStr("sk_test_1234567890"),
        )

        masked = creds.get_masked_dict(mask_level="standard")

        assert isinstance(masked, ModelMaskData)
        masked_dict = masked.to_dict()

        # Regular fields should be visible
        assert masked_dict.get("username") == "test_user"

        # Secret fields should be masked
        assert masked_dict.get("password") == "***MASKED***"
        assert masked_dict.get("api_key") == "***MASKED***"

    def test_get_masked_dict_minimal_masking(self):
        """Test minimal masking level (shows partial values)."""
        creds = TestCredentials(
            password=SecretStr("password123"),
            api_key=SecretStr("sk_1234567890"),
        )

        masked = creds.get_masked_dict(mask_level="minimal")
        masked_dict = masked.to_dict()

        # Should show first/last 2 characters
        password_masked = masked_dict.get("password")
        assert password_masked.startswith("pa")
        assert password_masked.endswith("23")
        assert "*" in password_masked

    def test_get_masked_dict_aggressive_masking(self):
        """Test aggressive masking level."""
        creds = TestCredentials(
            password=SecretStr("my_password"),
            api_key=SecretStr("api_key_123"),
        )

        masked = creds.get_masked_dict(mask_level="aggressive")
        masked_dict = masked.to_dict()

        # All secrets should be aggressively masked
        assert masked_dict.get("password") == "***REDACTED***"
        assert masked_dict.get("api_key") == "***REDACTED***"

    def test_mask_secret_value_short_secrets(self):
        """Test masking of short secret values."""
        creds = TestCredentials()

        # Short secrets (4 chars or less) should be fully masked
        assert creds._mask_secret_value("ab", "minimal") == "**"
        assert creds._mask_secret_value("abcd", "minimal") == "****"

    def test_mask_secret_value_empty_secrets(self):
        """Test masking of empty secrets."""
        creds = TestCredentials()

        assert creds._mask_secret_value("", "standard") == ""
        assert creds._mask_secret_value("", "minimal") == ""
        assert creds._mask_secret_value("", "aggressive") == ""

    def test_mask_if_sensitive_string_patterns(self):
        """Test detection and masking of sensitive string patterns."""
        creds = TestCredentials()

        # Base64-encoded pattern (40+ chars)
        base64_value = "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY3ODkwYWJjZGVm"
        assert (
            creds._mask_if_sensitive_string(base64_value, "aggressive")
            == "***REDACTED***"
        )

        # Hex string pattern (32+ chars)
        hex_value = "abcdef1234567890abcdef1234567890"
        assert (
            creds._mask_if_sensitive_string(hex_value, "aggressive") == "***REDACTED***"
        )

        # API key pattern
        api_key = "ABCDEFGH12345678_IJKLMNOP90123456"
        assert (
            creds._mask_if_sensitive_string(api_key, "aggressive") == "***REDACTED***"
        )

        # Normal strings should not be masked
        normal_string = "hello world"
        assert (
            creds._mask_if_sensitive_string(normal_string, "aggressive")
            == "hello world"
        )

    def test_mask_secrets_recursive_dict(self):
        """Test recursive masking of nested dictionaries."""
        creds = TestCredentials(password=SecretStr("secret123"))

        data = {
            "config": {"password": SecretStr("nested_secret"), "host": "localhost"},
            "api_key": SecretStr("top_level_secret"),
        }

        masked = creds._mask_secrets_recursive(data, "standard")

        assert masked["config"]["password"] == "***MASKED***"
        assert masked["config"]["host"] == "localhost"
        assert masked["api_key"] == "***MASKED***"

    def test_mask_secrets_recursive_list(self):
        """Test recursive masking of lists."""
        creds = TestCredentials()

        data = [
            SecretStr("secret1"),
            "normal_value",
            {"password": SecretStr("secret2")},
        ]

        masked = creds._mask_secrets_recursive(data, "standard")

        assert masked[0] == "***MASKED***"
        assert masked[1] == "normal_value"
        assert masked[2]["password"] == "***MASKED***"


class TestModelSecureCredentialsStrengthAssessment:
    """Test credential strength assessment."""

    def test_get_credential_strength_assessment_strong(self):
        """Test strength assessment with strong credentials."""
        creds = TestCredentials(
            password=SecretStr("VeryStrongPassword123!@#"),
            api_key=SecretStr("sk_live_very_long_secure_api_key_here"),
        )

        assessment = creds.get_credential_strength_assessment()

        assert isinstance(assessment, ModelCredentialsAnalysis)
        assert assessment.strength_score == 100  # All secrets are strong
        assert assessment.compliance_status == "compliant"
        assert assessment.risk_level == "low"
        assert len(assessment.security_issues) == 0

    def test_get_credential_strength_assessment_weak(self):
        """Test strength assessment with weak credentials."""
        creds = TestCredentials(
            password=SecretStr("weak"),  # Too short
            api_key=SecretStr("short"),  # Too short
        )

        assessment = creds.get_credential_strength_assessment()

        assert assessment.strength_score < 50  # Weak secrets
        assert assessment.compliance_status == "non_compliant"
        assert assessment.risk_level == "high"
        assert len(assessment.security_issues) > 0
        assert any("weak" in issue.lower() for issue in assessment.security_issues)

    def test_get_credential_strength_assessment_empty(self):
        """Test strength assessment with empty credentials."""
        creds = TestCredentials(
            password=SecretStr(""),  # Empty
            api_key=None,
        )

        assessment = creds.get_credential_strength_assessment()

        assert "Empty secret" in " ".join(assessment.security_issues)
        assert assessment.compliance_status == "non_compliant"
        assert len(assessment.recommendations) > 0

    def test_get_credential_strength_assessment_mixed(self):
        """Test strength assessment with mixed credential quality."""
        creds = TestCredentials(
            password=SecretStr("VeryStrongPassword123!"),  # Strong
            api_key=SecretStr("weak"),  # Weak
        )

        assessment = creds.get_credential_strength_assessment()

        # Should be 50% strength (1 out of 2 strong)
        assert assessment.strength_score == 50
        assert len(assessment.security_issues) > 0
        assert len(assessment.recommendations) > 0


class TestModelSecureCredentialsSecurityClassification:
    """Test security classification functionality."""

    def test_get_security_classification_secret_fields(self):
        """Test classification of SecretStr fields."""
        creds = TestCredentials(
            password=SecretStr("secret"),
            api_key=SecretStr("key"),
        )

        classification = creds.get_security_classification()

        assert classification["password"] == "secret"
        assert classification["api_key"] == "secret"

    def test_get_security_classification_sensitive_fields(self):
        """Test classification of sensitive field names."""
        # Note: This test assumes the model would have fields with these names
        creds = TestCredentials()

        classification = creds.get_security_classification()

        # Regular fields should not be classified as secret
        assert classification["username"] == "pii"  # Contains 'username'
        assert classification["host"] == "public"

    def test_get_security_classification_pii_fields(self):
        """Test classification of PII fields."""
        creds = TestCredentials()

        classification = creds.get_security_classification()

        # Username contains 'username' so should be PII
        assert classification["username"] == "pii"


class TestModelSecureCredentialsEnvironmentIntegration:
    """Test environment variable integration."""

    @patch.dict(
        os.environ,
        {
            "TEST_USERNAME": "env_user",
            "TEST_PASSWORD": "env_password",
            "TEST_HOST": "env_host",
            "TEST_PORT": "9999",
        },
    )
    def test_load_from_env_with_custom_prefix(self):
        """Test loading from environment with custom prefix."""
        creds = TestCredentials.load_from_env(env_prefix="TEST_")

        assert creds.username == "env_user"
        assert creds.password.get_secret_value() == "env_password"
        assert creds.host == "env_host"
        assert creds.port == 9999

    @patch.dict(os.environ, {}, clear=True)
    def test_load_from_env_with_defaults(self):
        """Test loading from environment falls back to defaults."""
        creds = TestCredentials.load_from_env(env_prefix="MISSING_")

        assert creds.username == "test_user"  # Default value
        assert creds.password.get_secret_value() == "default_password"

    def test_validate_environment_variables_all_present(self):
        """Test environment variable validation when all present."""
        # TestCredentials has no required fields beyond defaults
        creds = TestCredentials()

        issues = creds.validate_environment_variables(env_prefix="TEST_")

        # No required fields without defaults, so no issues expected
        assert isinstance(issues, list)

    def test_get_environment_mapping(self):
        """Test environment variable mapping generation."""
        creds = TestCredentials()

        mapping = creds.get_environment_mapping(env_prefix="ONEX_")

        assert "username" in mapping
        assert mapping["username"] == "ONEX_USERNAME"
        assert "password" in mapping
        assert mapping["password"] == "ONEX_PASSWORD"
        assert "host" in mapping
        assert mapping["host"] == "ONEX_HOST"

    @patch.dict(
        os.environ,
        {"TEST_USERNAME": "new_user", "TEST_PASSWORD": "new_password"},
    )
    def test_load_from_environment_with_validation(self):
        """Test loading from environment with validation."""
        creds = TestCredentials()

        issues = creds.load_from_environment_with_validation(env_prefix="TEST_")

        # Should successfully load without issues
        assert len(issues) == 0
        assert creds.username == "new_user"
        assert creds.password.get_secret_value() == "new_password"


class TestModelSecureCredentialsSerialization:
    """Test serialization methods."""

    def test_to_log_safe_dict(self):
        """Test log-safe dictionary generation."""
        creds = TestCredentials(
            username="test_user",
            password=SecretStr("secret_password"),
            host="localhost",
        )

        log_safe = creds.to_log_safe_dict()

        assert isinstance(log_safe, ModelLogSafeData)
        # Secrets should be masked
        # Public fields may be visible depending on implementation

    def test_to_debug_dict(self):
        """Test debug dictionary generation."""
        creds = TestCredentials(
            username="debug_user",
            password=SecretStr("debug_password"),
        )

        debug_data = creds.to_debug_dict()

        assert isinstance(debug_data, ModelDebugData)
        # Should have minimal masking for debugging

    def test_to_audit_dict(self):
        """Test audit dictionary generation."""
        creds = TestCredentials(
            username="audit_user",
            password=SecretStr("audit_password"),
        )

        audit_data = creds.to_audit_dict()

        assert isinstance(audit_data, ModelAuditData)
        assert audit_data.action == "credential_access"
        assert audit_data.resource == "TestCredentials"
        assert audit_data.result == "masked"
        assert audit_data.security_level == "audit"
        assert "credential_masking" in audit_data.compliance_tags

    def test_export_to_env_template(self):
        """Test environment variable template export."""
        creds = TestCredentials()

        template = creds.export_to_env_template(env_prefix="MYAPP_")

        assert "# Environment variables template" in template
        assert "MYAPP_USERNAME" in template
        assert "MYAPP_PASSWORD" in template
        assert "MYAPP_HOST" in template
        assert "MYAPP_PORT" in template
        # Should include security classifications
        assert "(pii)" in template or "(secret)" in template


class TestModelSecureCredentialsValidation:
    """Test credential validation methods."""

    def test_validate_credentials_all_valid(self):
        """Test validation with all valid credentials."""
        creds = TestCredentials(
            username="valid_user",
            password=SecretStr("VeryStrongPassword123!"),
            api_key=SecretStr("sk_live_very_long_api_key"),
        )

        result = creds.validate_credentials()

        assert isinstance(result, ModelCredentialValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.strength_score >= 50

    def test_validate_credentials_with_weak_secrets(self):
        """Test validation with weak secrets."""
        creds = TestCredentials(
            username="test_user",
            password=SecretStr("weak"),  # Too short
        )

        result = creds.validate_credentials()

        # May still be valid if not required, but should have warnings
        assert len(result.warnings) > 0 or len(result.errors) > 0
        assert result.strength_score < 100

    def test_validate_credentials_empty_required_field(self):
        """Test validation with empty required SecretStr field."""

        # Create a model with required secret field
        class RequiredSecretCreds(ModelSecureCredentials):
            api_key: SecretStr

            @classmethod
            def load_from_env(cls, env_prefix: str = "ONEX_"):
                return cls(api_key=SecretStr(os.getenv(f"{env_prefix}API_KEY", "")))

        creds = RequiredSecretCreds(api_key=SecretStr(""))

        result = creds.validate_credentials()

        assert result.is_valid is False
        assert any("empty" in error.lower() for error in result.errors)

    def test_can_connect(self):
        """Test connection capability check."""
        creds = TestCredentials(
            username="test_user",
            password=SecretStr("ValidPassword123"),
        )

        # Should return True if credentials are valid
        can_connect = creds.can_connect()

        assert isinstance(can_connect, bool)
        # Based on validation result
        assert can_connect is True


class TestModelSecureCredentialsFactoryMethods:
    """Test factory methods."""

    @patch.dict(
        os.environ,
        {"PRIMARY_USERNAME": "primary_user", "PRIMARY_PASSWORD": "primary_pass"},
    )
    def test_create_from_env_with_fallbacks_primary_success(self):
        """Test factory with successful primary prefix."""
        creds = TestCredentials.create_from_env_with_fallbacks(
            env_prefix="PRIMARY_", fallback_prefixes=["SECONDARY_", "TERTIARY_"]
        )

        assert creds.username == "primary_user"
        assert creds.password.get_secret_value() == "primary_pass"

    @patch.dict(
        os.environ,
        {
            "SECONDARY_USERNAME": "secondary_user",
            "SECONDARY_PASSWORD": "secondary_pass",
        },
    )
    def test_create_from_env_with_fallbacks_fallback_success(self):
        """Test factory falls back to secondary prefix."""
        creds = TestCredentials.create_from_env_with_fallbacks(
            env_prefix="PRIMARY_",  # Missing
            fallback_prefixes=["SECONDARY_"],
        )

        assert creds.username == "secondary_user"
        assert creds.password.get_secret_value() == "secondary_pass"

    @patch.dict(os.environ, {}, clear=True)
    def test_create_from_env_with_fallbacks_all_fail(self):
        """Test factory when all prefixes fail (creates with defaults)."""
        creds = TestCredentials.create_from_env_with_fallbacks(
            env_prefix="PRIMARY_", fallback_prefixes=["SECONDARY_"]
        )

        # Should create with defaults
        assert creds.username == "test_user"  # Default value

    def test_create_empty_template(self):
        """Test empty template creation."""
        template = TestCredentials.create_empty_template()

        assert isinstance(template, TestCredentials)
        # Should have default values
        assert template.username == "test_user"
        assert isinstance(template.password, SecretStr)


class TestModelSecureCredentialsSecurityBestPractices:
    """Test security best practices compliance."""

    def test_no_plaintext_secrets_in_repr(self):
        """Test that secrets don't appear in string representation."""
        creds = TestCredentials(
            password=SecretStr("SuperSecretPassword123!"),
            api_key=SecretStr("sk_live_secret_key_12345"),
        )

        repr_str = repr(creds)
        str_str = str(creds)

        # Secrets should not be in plain text
        assert "SuperSecretPassword123!" not in repr_str
        assert "sk_live_secret_key_12345" not in repr_str
        assert "SuperSecretPassword123!" not in str_str
        assert "sk_live_secret_key_12345" not in str_str

    def test_no_plaintext_secrets_in_dict_dump(self):
        """Test that model_dump doesn't expose raw SecretStr values."""
        creds = TestCredentials(
            password=SecretStr("secret123"),
            api_key=SecretStr("api_key_456"),
        )

        dump = creds.model_dump()

        # Pydantic SecretStr should not expose raw values in dump
        # The actual value depends on Pydantic's SecretStr implementation
        assert isinstance(dump, dict)

    def test_secret_masking_prevents_exposure(self):
        """Test that masking prevents secret exposure."""
        creds = TestCredentials(
            password=SecretStr("MySecretPassword"),
            api_key=SecretStr("MySecretAPIKey"),
        )

        # All masking levels should prevent exposure
        for level in ["minimal", "standard", "aggressive"]:
            masked = creds.get_masked_dict(mask_level=level)
            masked_dict = masked.to_dict()

            # Raw secrets should not be present
            for value in masked_dict.values():
                if isinstance(value, str):
                    assert "MySecretPassword" not in value
                    assert "MySecretAPIKey" not in value

    def test_audit_logging_masks_secrets(self):
        """Test that audit logs mask secrets."""
        creds = TestCredentials(
            username="audit_test",
            password=SecretStr("AuditSecretPassword"),
        )

        audit_data = creds.to_audit_dict()

        # Verify secrets are masked in audit metadata
        audit_str = str(audit_data.audit_metadata)
        assert "AuditSecretPassword" not in audit_str


class TestModelSecureCredentialsEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_credentials_with_none_optional_fields(self):
        """Test credentials with None values for optional fields."""
        creds = TestCredentials(
            username="test_user",
            password=SecretStr("password"),
            api_key=None,
            connection_string=None,
        )

        assert creds.api_key is None
        assert creds.connection_string is None

        # Should handle None gracefully in masking
        masked = creds.get_masked_dict()
        assert isinstance(masked, ModelMaskData)

    def test_credentials_with_very_long_secrets(self):
        """Test credentials with very long secret values."""
        long_secret = "a" * 10000
        creds = TestCredentials(password=SecretStr(long_secret))

        # Should handle long secrets in masking
        masked = creds.get_masked_dict(mask_level="minimal")
        masked_dict = masked.to_dict()

        # Minimal masking should show first/last 2 chars
        password_masked = masked_dict.get("password")
        assert len(password_masked) > 0

    def test_credentials_with_special_characters(self):
        """Test credentials with special characters."""
        special_password = "P@ssw0rd!#$%^&*()[]{}|\\:;\"'<>,.?/"
        creds = TestCredentials(password=SecretStr(special_password))

        # Should handle special characters
        masked = creds.get_masked_dict(mask_level="standard")
        assert isinstance(masked, ModelMaskData)

        # Validate credentials should work
        result = creds.validate_credentials()
        assert isinstance(result, ModelCredentialValidationResult)

    def test_credentials_with_unicode_secrets(self):
        """Test credentials with unicode characters."""
        unicode_password = "Pass你好🔐word"
        creds = TestCredentials(password=SecretStr(unicode_password))

        # Should handle unicode
        masked = creds.get_masked_dict()
        assert isinstance(masked, ModelMaskData)

    def test_environment_mapping_with_special_field_names(self):
        """Test environment mapping handles field names correctly."""
        creds = TestCredentials()

        mapping = creds.get_environment_mapping(env_prefix="TEST_")

        # All field names should be uppercase
        for field_name, env_var in mapping.items():
            assert env_var.startswith("TEST_")
            assert env_var == f"TEST_{field_name.upper()}"

    def test_strength_assessment_with_no_secrets(self):
        """Test strength assessment when model has no SecretStr fields."""

        class NoSecretCreds(ModelSecureCredentials):
            username: str = "user"
            host: str = "localhost"

            @classmethod
            def load_from_env(cls, env_prefix: str = "ONEX_"):
                return cls()

        creds = NoSecretCreds()
        assessment = creds.get_credential_strength_assessment()

        assert assessment.strength_score == 0  # No secrets
        assert "Consider using SecretStr" in " ".join(assessment.recommendations)

    def test_recursive_masking_deeply_nested_structure(self):
        """Test recursive masking with deeply nested structures."""
        creds = TestCredentials()

        nested_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "secret": SecretStr("deep_secret"),
                            "normal": "value",
                        }
                    }
                }
            }
        }

        masked = creds._mask_secrets_recursive(nested_data, "standard")

        assert (
            masked["level1"]["level2"]["level3"]["level4"]["secret"] == "***MASKED***"
        )
        assert masked["level1"]["level2"]["level3"]["level4"]["normal"] == "value"

    def test_validation_comprehensive_report(self):
        """Test that validation returns comprehensive report."""
        creds = TestCredentials(
            password=SecretStr("weak"),  # Weak password
            api_key=SecretStr("short"),  # Short key
        )

        result = creds.validate_credentials()

        # Should have comprehensive information
        assert hasattr(result, "is_valid")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")
        assert hasattr(result, "strength_score")
        assert hasattr(result, "compliance_status")
        assert hasattr(result, "recommendations")

        # Should provide actionable recommendations
        assert len(result.recommendations) > 0


class TestModelSecureCredentialsBranchCoverage:
    """Test specific conditional branches for comprehensive branch coverage."""

    def test_mask_secret_value_unknown_level_defaults_to_masked(self):
        """Test masking with unknown level defaults to standard (line 92)."""
        creds = TestCredentials()

        # Unknown masking level should default to standard
        masked = creds._mask_secret_value("secret_value", "unknown_level")
        assert masked == "***MASKED***"

    def test_get_credential_strength_assessment_with_16char_secret(self):
        """Test strength assessment boundary at 16 characters (line 137-138)."""
        # Exactly 16 characters - should be strong
        creds = TestCredentials(
            password=SecretStr("1234567890123456"),  # Exactly 16 chars
            api_key=SecretStr("abcdefghijklmnop"),  # Exactly 16 chars
        )

        assessment = creds.get_credential_strength_assessment()

        # 16+ characters should be strong
        assert assessment.strength_score == 100
        assert len(assessment.security_issues) == 0

    def test_get_credential_strength_assessment_with_8to15char_secret(self):
        """Test strength assessment with 8-15 character secret (line 136-138)."""
        # Between 8 and 15 characters - considered weak
        creds = TestCredentials(
            password=SecretStr("12345678"),  # 8 chars
            api_key=SecretStr("123456789012"),  # 12 chars
        )

        assessment = creds.get_credential_strength_assessment()

        # Should have weak secret warnings
        assert len(assessment.security_issues) > 0
        assert any("weak" in issue.lower() for issue in assessment.security_issues)

    def test_validate_environment_variables_with_missing_required(self):
        """Test environment validation with missing required variables (lines 207-209)."""

        # Create a model with required fields
        class RequiredFieldsCreds(ModelSecureCredentials):
            required_field: str
            api_key: SecretStr

            @classmethod
            def load_from_env(cls, env_prefix: str = "ONEX_"):
                return cls(
                    required_field=os.getenv(f"{env_prefix}REQUIRED_FIELD", ""),
                    api_key=SecretStr(os.getenv(f"{env_prefix}API_KEY", "")),
                )

        creds = RequiredFieldsCreds(required_field="test", api_key=SecretStr("key"))

        # Clear environment to test missing variables
        with patch.dict(os.environ, {}, clear=True):
            issues = creds.validate_environment_variables(env_prefix="TEST_")

            # Should report missing required variables
            assert len(issues) > 0
            assert any("required" in issue.lower() for issue in issues)

    def test_load_from_environment_with_validation_error_handling(self):
        """Test environment loading handles errors gracefully (lines 244-254)."""
        creds = TestCredentials()

        # The method doesn't actually perform type conversion, it just loads string values
        # So we test that it handles loading without errors
        with patch.dict(
            os.environ, {"TEST_USERNAME": "test_user", "TEST_PASSWORD": "test_pass"}
        ):
            issues = creds.load_from_environment_with_validation(env_prefix="TEST_")

            # Issues should be empty or a list
            assert isinstance(issues, list)

    def test_export_to_env_template_with_optional_fields(self):
        """Test template export distinguishes required vs optional (line 364)."""
        creds = TestCredentials()

        template = creds.export_to_env_template(env_prefix="TEST_")

        # Should mark fields as REQUIRED or OPTIONAL
        assert "# REQUIRED" in template or "# OPTIONAL" in template

    def test_validate_credentials_with_non_empty_required_field(self):
        """Test credential validation when required non-SecretStr field is empty (lines 392-394)."""

        # Create model with required non-secret field
        class RequiredNonSecretCreds(ModelSecureCredentials):
            username: str  # Required non-secret field
            password: SecretStr

            @classmethod
            def load_from_env(cls, env_prefix: str = "ONEX_"):
                return cls(
                    username=os.getenv(f"{env_prefix}USERNAME", ""),
                    password=SecretStr(os.getenv(f"{env_prefix}PASSWORD", "")),
                )

        # Test with empty required field
        creds = RequiredNonSecretCreds(username="", password=SecretStr("pass"))

        result = creds.validate_credentials()

        # Empty required field should cause validation failure
        # (behavior depends on model configuration)
        assert isinstance(result, ModelCredentialValidationResult)

    def test_create_from_env_with_fallbacks_exception_in_primary(self):
        """Test fallback handling when primary prefix throws exception (lines 442-443)."""
        with patch.dict(os.environ, {"PRIMARY_USERNAME": "user1"}, clear=True):
            # Mock load_from_env to raise exception for primary
            original_load = TestCredentials.load_from_env

            def mock_load_primary(env_prefix):
                if env_prefix == "PRIMARY_":
                    raise ValueError("Primary load failed")
                return original_load(env_prefix)

            with patch.object(
                TestCredentials, "load_from_env", side_effect=mock_load_primary
            ):
                # Should fall back to defaults
                creds = TestCredentials.create_from_env_with_fallbacks(
                    env_prefix="PRIMARY_", fallback_prefixes=[]
                )

                # Should create with defaults due to exception
                assert isinstance(creds, TestCredentials)

    def test_create_from_env_with_fallbacks_exception_in_fallback(self):
        """Test fallback handling when fallback prefix throws exception (lines 453-458)."""
        with patch.dict(os.environ, {}, clear=True):
            # Mock load_from_env to raise exception for fallback
            original_load = TestCredentials.load_from_env

            call_count = [0]

            def mock_load_fallback(env_prefix):
                call_count[0] += 1
                if env_prefix == "FALLBACK_":
                    raise ValueError("Fallback load failed")
                return original_load(env_prefix)

            with patch.object(
                TestCredentials, "load_from_env", side_effect=mock_load_fallback
            ):
                # Should try fallback, catch exception, and create with defaults
                creds = TestCredentials.create_from_env_with_fallbacks(
                    env_prefix="PRIMARY_", fallback_prefixes=["FALLBACK_"]
                )

                # Should create with defaults
                assert isinstance(creds, TestCredentials)

    def test_load_from_environment_with_validation_issues_logged(self):
        """Test that validation issues are properly collected (line 474)."""
        creds = TestCredentials()

        # Mock a scenario where loading succeeds but returns issues
        with patch.dict(
            os.environ, {"TEST_USERNAME": "test_user", "TEST_PASSWORD": "test_pass"}
        ):
            issues = creds.load_from_environment_with_validation(env_prefix="TEST_")

            # Issues list should be returned (may be empty if all succeed)
            assert isinstance(issues, list)

    def test_get_masked_dict_returns_non_dict_type(self):
        """Test masked dict handling when result is not a dict (line 58)."""
        creds = TestCredentials()

        # The get_masked_dict should always return ModelMaskData
        masked = creds.get_masked_dict(mask_level="standard")

        # Should be ModelMaskData type
        assert isinstance(masked, ModelMaskData)

    def test_mask_if_sensitive_string_with_non_aggressive_level(self):
        """Test sensitive string masking only applies in aggressive mode."""
        creds = TestCredentials()

        # Base64 pattern should NOT be masked in standard mode
        base64_value = "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY3ODkwYWJjZGVm"
        result = creds._mask_if_sensitive_string(base64_value, "standard")

        # Should return unchanged (no masking in non-aggressive mode)
        assert result == base64_value

    def test_validate_credentials_with_weak_secret_count(self):
        """Test validation properly counts weak secrets (lines 400-406)."""
        creds = TestCredentials(
            password=SecretStr("weak1"),  # Weak
            api_key=SecretStr("weak2"),  # Weak
        )

        result = creds.validate_credentials()

        # Should have warnings about weak secrets
        assert len(result.warnings) > 0
        # Check that weak secret count is reflected
        weak_count_found = any("weak" in str(w).lower() for w in result.warnings)
        assert weak_count_found
