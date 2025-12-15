"""
Unit tests for ModelWorkflowStateSnapshot PII sanitization.

Tests the sanitize_context_for_logging() class method including:
- Email address redaction
- Phone number redaction (various formats)
- SSN redaction
- Credit card number redaction
- IP address redaction
- Nested dict/list sanitization
- Key-based redaction
- Custom pattern support
- Type preservation for non-string values
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from omnibase_core.models.workflow import ModelWorkflowStateSnapshot

pytestmark = pytest.mark.unit


class TestSanitizeContextForLoggingEmailRedaction:
    """Test email address redaction in sanitize_context_for_logging."""

    def test_redacts_simple_email(self) -> None:
        """Test redaction of a simple email address."""
        context = {"email": "john.doe@example.com"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["email"] == "[EMAIL_REDACTED]"

    def test_redacts_email_with_plus_sign(self) -> None:
        """Test redaction of email with plus sign."""
        context = {"email": "john+tag@example.com"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["email"] == "[EMAIL_REDACTED]"

    def test_redacts_email_with_subdomain(self) -> None:
        """Test redaction of email with subdomain."""
        context = {"email": "user@mail.company.co.uk"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["email"] == "[EMAIL_REDACTED]"

    def test_redacts_multiple_emails_in_string(self) -> None:
        """Test redaction of multiple emails in a single string."""
        context = {"message": "Contact john@test.com or jane@test.com"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["message"] == "Contact [EMAIL_REDACTED] or [EMAIL_REDACTED]"

    def test_preserves_non_email_strings(self) -> None:
        """Test that non-email strings are preserved."""
        context = {"name": "John Doe", "status": "active"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["name"] == "John Doe"
        assert result["status"] == "active"


class TestSanitizeContextForLoggingPhoneRedaction:
    """Test phone number redaction in sanitize_context_for_logging."""

    def test_redacts_phone_with_dashes(self) -> None:
        """Test redaction of phone number with dashes."""
        context = {"phone": "555-123-4567"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["phone"] == "[PHONE_REDACTED]"

    def test_redacts_phone_with_dots(self) -> None:
        """Test redaction of phone number with dots."""
        context = {"phone": "555.123.4567"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["phone"] == "[PHONE_REDACTED]"

    def test_redacts_phone_with_spaces(self) -> None:
        """Test redaction of phone number with spaces."""
        context = {"phone": "555 123 4567"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["phone"] == "[PHONE_REDACTED]"

    def test_redacts_phone_with_parentheses(self) -> None:
        """Test redaction of phone number with parentheses."""
        context = {"phone": "(555) 123-4567"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["phone"] == "[PHONE_REDACTED]"

    def test_redacts_phone_with_country_code(self) -> None:
        """Test redaction of phone number with +1 country code."""
        context = {"phone": "+1-555-123-4567"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["phone"] == "[PHONE_REDACTED]"

    def test_redacts_plain_phone_number(self) -> None:
        """Test redaction of plain 10-digit phone number."""
        context = {"phone": "5551234567"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["phone"] == "[PHONE_REDACTED]"


class TestSanitizeContextForLoggingSSNRedaction:
    """Test SSN redaction in sanitize_context_for_logging."""

    def test_redacts_ssn_with_dashes(self) -> None:
        """Test redaction of SSN with dashes."""
        context = {"ssn": "123-45-6789"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["ssn"] == "[SSN_REDACTED]"

    def test_redacts_ssn_with_spaces(self) -> None:
        """Test redaction of SSN with spaces."""
        context = {"ssn": "123 45 6789"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["ssn"] == "[SSN_REDACTED]"

    def test_redacts_plain_ssn(self) -> None:
        """Test redaction of plain 9-digit SSN."""
        context = {"ssn": "123456789"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["ssn"] == "[SSN_REDACTED]"


class TestSanitizeContextForLoggingCreditCardRedaction:
    """Test credit card number redaction in sanitize_context_for_logging."""

    def test_redacts_credit_card_with_dashes(self) -> None:
        """Test redaction of credit card with dashes."""
        context = {"card": "4111-1111-1111-1111"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["card"] == "[CREDIT_CARD_REDACTED]"

    def test_redacts_credit_card_with_spaces(self) -> None:
        """Test redaction of credit card with spaces."""
        context = {"card": "4111 1111 1111 1111"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["card"] == "[CREDIT_CARD_REDACTED]"

    def test_redacts_plain_credit_card(self) -> None:
        """Test redaction of plain 16-digit credit card."""
        context = {"card": "4111111111111111"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["card"] == "[CREDIT_CARD_REDACTED]"


class TestSanitizeContextForLoggingIPRedaction:
    """Test IP address redaction in sanitize_context_for_logging."""

    def test_redacts_ipv4_address(self) -> None:
        """Test redaction of IPv4 address."""
        context = {"ip": "192.168.1.100"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["ip"] == "[IP_REDACTED]"

    def test_redacts_ip_in_log_message(self) -> None:
        """Test redaction of IP address in log message."""
        context = {"log": "Connection from 10.0.0.1 established"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["log"] == "Connection from [IP_REDACTED] established"


class TestSanitizeContextForLoggingNestedStructures:
    """Test nested dict/list sanitization in sanitize_context_for_logging."""

    def test_sanitizes_nested_dict(self) -> None:
        """Test sanitization of nested dict."""
        context = {
            "user": {
                "email": "user@test.com",
                "profile": {"phone": "555-123-4567"},
            }
        }
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["user"]["email"] == "[EMAIL_REDACTED]"
        assert result["user"]["profile"]["phone"] == "[PHONE_REDACTED]"

    def test_sanitizes_list_of_strings(self) -> None:
        """Test sanitization of list containing strings."""
        context = {"emails": ["user1@test.com", "user2@test.com"]}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["emails"] == ["[EMAIL_REDACTED]", "[EMAIL_REDACTED]"]

    def test_sanitizes_list_of_dicts(self) -> None:
        """Test sanitization of list containing dicts."""
        context = {
            "users": [
                {"email": "user1@test.com"},
                {"email": "user2@test.com"},
            ]
        }
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["users"][0]["email"] == "[EMAIL_REDACTED]"
        assert result["users"][1]["email"] == "[EMAIL_REDACTED]"

    def test_sanitizes_tuple(self) -> None:
        """Test sanitization of tuple values."""
        context = {"emails": ("user1@test.com", "user2@test.com")}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["emails"] == ("[EMAIL_REDACTED]", "[EMAIL_REDACTED]")
        assert isinstance(result["emails"], tuple)


class TestSanitizeContextForLoggingKeyRedaction:
    """Test key-based redaction in sanitize_context_for_logging."""

    def test_redacts_specified_keys(self) -> None:
        """Test that specified keys are fully redacted."""
        context = {
            "password": "secret123",
            "api_key": "abc123xyz",
            "normal_field": "visible",
        }
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(
            context, redact_keys=["password", "api_key"]
        )
        assert result["password"] == "[REDACTED]"
        assert result["api_key"] == "[REDACTED]"
        assert result["normal_field"] == "visible"

    def test_key_redaction_is_case_insensitive(self) -> None:
        """Test that key redaction is case-insensitive."""
        context = {
            "PASSWORD": "secret1",
            "Password": "secret2",
            "password": "secret3",
        }
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(
            context, redact_keys=["password"]
        )
        assert result["PASSWORD"] == "[REDACTED]"
        assert result["Password"] == "[REDACTED]"
        assert result["password"] == "[REDACTED]"

    def test_key_redaction_in_nested_dict(self) -> None:
        """Test key redaction in nested dict."""
        context = {
            "config": {
                "api_key": "secret",
                "url": "https://example.com",
            }
        }
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(
            context, redact_keys=["api_key"]
        )
        assert result["config"]["api_key"] == "[REDACTED]"
        assert result["config"]["url"] == "https://example.com"


class TestSanitizeContextForLoggingCustomPatterns:
    """Test custom pattern support in sanitize_context_for_logging."""

    def test_applies_custom_patterns(self) -> None:
        """Test that custom patterns are applied."""
        context = {"token": "JWT-abc123xyz"}
        custom_patterns = [(r"JWT-\w+", "[JWT_REDACTED]")]
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(
            context, additional_patterns=custom_patterns
        )
        assert result["token"] == "[JWT_REDACTED]"

    def test_custom_patterns_applied_after_defaults(self) -> None:
        """Test that custom patterns are applied after default patterns."""
        context = {"data": "email: user@test.com, token: abc123"}
        custom_patterns = [(r"abc123", "[TOKEN_REDACTED]")]
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(
            context, additional_patterns=custom_patterns
        )
        assert "[EMAIL_REDACTED]" in result["data"]
        assert "[TOKEN_REDACTED]" in result["data"]


class TestSanitizeContextForLoggingTypePreservation:
    """Test that non-string types are preserved in sanitize_context_for_logging."""

    def test_preserves_integers(self) -> None:
        """Test that integer values are preserved."""
        context = {"count": 42, "id": 12345}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["count"] == 42
        assert result["id"] == 12345

    def test_preserves_floats(self) -> None:
        """Test that float values are preserved."""
        context = {"ratio": 3.14, "percentage": 0.75}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["ratio"] == 3.14
        assert result["percentage"] == 0.75

    def test_preserves_booleans(self) -> None:
        """Test that boolean values are preserved."""
        context = {"active": True, "deleted": False}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["active"] is True
        assert result["deleted"] is False

    def test_preserves_none(self) -> None:
        """Test that None values are preserved."""
        context = {"optional_field": None}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["optional_field"] is None

    def test_preserves_uuid(self) -> None:
        """Test that UUID values are preserved."""
        test_uuid = uuid4()
        context = {"workflow_id": test_uuid}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["workflow_id"] == test_uuid

    def test_preserves_datetime(self) -> None:
        """Test that datetime values are preserved."""
        test_dt = datetime.now(UTC)
        context = {"created_at": test_dt}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["created_at"] == test_dt


class TestSanitizeContextForLoggingOriginalPreservation:
    """Test that original context is not modified by sanitize_context_for_logging."""

    def test_does_not_modify_original_context(self) -> None:
        """Test that the original context dict is not modified."""
        original = {
            "email": "user@test.com",
            "nested": {"phone": "555-123-4567"},
        }
        original_copy = {
            "email": "user@test.com",
            "nested": {"phone": "555-123-4567"},
        }

        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(original)

        # Original should be unchanged
        assert original == original_copy
        assert original["email"] == "user@test.com"
        assert original["nested"]["phone"] == "555-123-4567"

        # Result should be sanitized
        assert result["email"] == "[EMAIL_REDACTED]"
        assert result["nested"]["phone"] == "[PHONE_REDACTED]"


class TestSanitizeContextForLoggingEdgeCases:
    """Test edge cases for sanitize_context_for_logging."""

    def test_empty_context(self) -> None:
        """Test sanitization of empty context."""
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging({})
        assert result == {}

    def test_empty_string_value(self) -> None:
        """Test sanitization of empty string value."""
        context = {"empty": ""}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["empty"] == ""

    def test_deeply_nested_structure(self) -> None:
        """Test sanitization of deeply nested structure."""
        context = {
            "level1": {"level2": {"level3": {"level4": {"email": "deep@test.com"}}}}
        }
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert (
            result["level1"]["level2"]["level3"]["level4"]["email"]
            == "[EMAIL_REDACTED]"
        )

    def test_mixed_types_in_list(self) -> None:
        """Test sanitization of list with mixed types."""
        context = {
            "data": [
                "user@test.com",
                42,
                True,
                None,
                {"phone": "555-123-4567"},
            ]
        }
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["data"][0] == "[EMAIL_REDACTED]"
        assert result["data"][1] == 42
        assert result["data"][2] is True
        assert result["data"][3] is None
        assert result["data"][4]["phone"] == "[PHONE_REDACTED]"

    def test_no_additional_patterns_or_redact_keys(self) -> None:
        """Test that default behavior works when optional params are None."""
        context = {"email": "user@test.com"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(
            context, additional_patterns=None, redact_keys=None
        )
        assert result["email"] == "[EMAIL_REDACTED]"


class TestSanitizeContextForLoggingIPv6Redaction:
    """Test IPv6 address redaction in sanitize_context_for_logging."""

    def test_redacts_full_ipv6_address(self) -> None:
        """Test redaction of full IPv6 address."""
        context = {"ip": "2001:0db8:85a3:0000:0000:8a2e:0370:7334"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["ip"] == "[IPV6_REDACTED]"

    def test_redacts_compressed_ipv6_address(self) -> None:
        """Test redaction of compressed IPv6 address with ::."""
        context = {"ip": "2001:db8::1"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["ip"] == "[IPV6_REDACTED]"

    def test_redacts_ipv6_loopback(self) -> None:
        """Test redaction of IPv6 loopback address ::1."""
        context = {"ip": "::1"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["ip"] == "[IPV6_REDACTED]"

    def test_redacts_ipv6_unspecified(self) -> None:
        """Test redaction of IPv6 unspecified address ::."""
        context = {"ip": "::"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["ip"] == "[IPV6_REDACTED]"

    def test_redacts_ipv6_link_local(self) -> None:
        """Test redaction of IPv6 link-local address."""
        context = {"ip": "fe80::1"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["ip"] == "[IPV6_REDACTED]"


class TestSanitizeContextForLoggingAPIKeyRedaction:
    """Test API key redaction in sanitize_context_for_logging.

    NOTE: Stripe API key tests (sk_live_, sk_test_, pk_live_) are intentionally
    omitted. GitHub's push protection blocks ANY string matching Stripe key
    patterns, even obviously fake test values. The regex patterns for Stripe
    keys are tested implicitly through the pattern structure - they follow the
    same pattern as other API key tests.
    """

    def test_redacts_aws_access_key(self) -> None:
        """Test redaction of AWS access key."""
        context = {"key": "AKIAIOSFODNN7EXAMPLE"}  # gitleaks:allow
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["key"] == "[API_KEY_REDACTED]"

    def test_redacts_github_pat(self) -> None:
        """Test redaction of GitHub personal access token."""
        # Pattern requires exactly 36 alphanumeric chars after ghp_ (use letters only)
        # gitleaks:allow - intentional test fixture for PII redaction testing
        context = {"key": "ghp_abcdefghijklmnopqrstuvwxyzABCDEFGHIJ"}  # 36 chars
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["key"] == "[API_KEY_REDACTED]"

    def test_redacts_github_oauth_token(self) -> None:
        """Test redaction of GitHub OAuth token."""
        # Pattern requires exactly 36 alphanumeric chars after gho_ (use letters only)
        # gitleaks:allow - intentional test fixture for PII redaction testing
        context = {"key": "gho_abcdefghijklmnopqrstuvwxyzABCDEFGHIJ"}  # 36 chars
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["key"] == "[API_KEY_REDACTED]"

    def test_redacts_slack_token(self) -> None:
        """Test redaction of Slack token."""
        # Use letters to avoid phone number pattern matching first
        # gitleaks:allow - intentional test fixture for PII redaction testing
        context = {"key": "xoxb-abcdefghijk-lmnopqrstuv-wxyzABCDEFGH"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["key"] == "[API_KEY_REDACTED]"


class TestSanitizeContextForLoggingUUIDRedaction:
    """Test UUID/GUID redaction in sanitize_context_for_logging.

    NOTE: UUID redaction is opt-in (redact_uuids=False by default) because UUIDs
    are often system-generated identifiers (workflow_id, step_id, correlation_id)
    useful for debugging, not personally identifiable information.
    """

    def test_redacts_standard_uuid(self) -> None:
        """Test redaction of standard UUID format when redact_uuids=True."""
        context = {"id": "550e8400-e29b-41d4-a716-446655440000"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(
            context, redact_uuids=True
        )
        assert result["id"] == "[UUID_REDACTED]"

    def test_redacts_uppercase_uuid(self) -> None:
        """Test redaction of uppercase UUID when redact_uuids=True."""
        context = {"id": "550E8400-E29B-41D4-A716-446655440000"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(
            context, redact_uuids=True
        )
        assert result["id"] == "[UUID_REDACTED]"

    def test_redacts_uuid_in_text(self) -> None:
        """Test redaction of UUID embedded in text when redact_uuids=True."""
        context = {"log": "User 550e8400-e29b-41d4-a716-446655440000 logged in"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(
            context, redact_uuids=True
        )
        assert result["log"] == "User [UUID_REDACTED] logged in"

    def test_preserves_uuid_strings_by_default(self) -> None:
        """Test that UUID strings are NOT redacted by default (redact_uuids=False).

        UUIDs are often system-generated identifiers useful for debugging,
        so they are preserved unless explicitly requested to be redacted.
        """
        context = {"workflow_id": "550e8400-e29b-41d4-a716-446655440000"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        # UUID strings should be preserved by default
        assert result["workflow_id"] == "550e8400-e29b-41d4-a716-446655440000"

    def test_preserves_uuid_objects(self) -> None:
        """Test that UUID objects (not strings) are preserved regardless of setting."""
        test_uuid = uuid4()
        context = {"workflow_id": test_uuid}
        # Even with redact_uuids=True, UUID objects are preserved
        # (only string representations are redacted)
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(
            context, redact_uuids=True
        )
        assert result["workflow_id"] == test_uuid


class TestSanitizeContextForLoggingGitHubFinegrainedPAT:
    """Test GitHub fine-grained PAT redaction in sanitize_context_for_logging."""

    def test_redacts_github_finegrained_pat(self) -> None:
        """Test redaction of GitHub fine-grained personal access token."""
        # Pattern requires github_pat_ prefix with 22+ alphanumeric/underscore chars
        # Using letters only to avoid triggering phone number pattern
        # gitleaks:allow - intentional test fixture for PII redaction testing
        context = {"key": "github_pat_abcdefghijklmnopqrstuvwxyzAB"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["key"] == "[API_KEY_REDACTED]"


class TestSanitizeContextForLoggingGenericAPIKey:
    """Test generic API key redaction in sanitize_context_for_logging."""

    def test_redacts_generic_api_key_underscore(self) -> None:
        """Test redaction of generic api_key_ prefix pattern."""
        # gitleaks:allow - intentional test fixture for PII redaction testing
        context = {"key": "api_key_abcdefghijklmnopqrstuvwxyz"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["key"] == "[API_KEY_REDACTED]"

    def test_redacts_generic_apikey_no_separator(self) -> None:
        """Test redaction of generic apikey prefix pattern."""
        # gitleaks:allow - intentional test fixture for PII redaction testing
        context = {"key": "apikeyabcdefghijklmnopqrstuvwxyz"}
        result = ModelWorkflowStateSnapshot.sanitize_context_for_logging(context)
        assert result["key"] == "[API_KEY_REDACTED]"


class TestValidateNoPII:
    """Test the validate_no_pii() class method for PII detection."""

    def test_detects_email_pattern(self) -> None:
        """Test detection of email address pattern."""
        context = {"email": "user@example.com"}
        is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii(context)
        assert is_valid is False
        assert len(violations) == 1
        assert "EMAIL" in violations[0]
        assert "email" in violations[0]

    def test_detects_phone_pattern(self) -> None:
        """Test detection of phone number pattern."""
        context = {"phone": "555-123-4567"}
        is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii(context)
        assert is_valid is False
        assert len(violations) == 1
        assert "PHONE" in violations[0]

    def test_detects_ssn_pattern(self) -> None:
        """Test detection of SSN pattern."""
        context = {"ssn": "123-45-6789"}
        is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii(context)
        assert is_valid is False
        assert len(violations) == 1
        assert "SSN" in violations[0]

    def test_detects_credit_card_pattern(self) -> None:
        """Test detection of credit card pattern."""
        context = {"card": "4111-1111-1111-1111"}
        is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii(context)
        assert is_valid is False
        assert len(violations) == 1
        assert "CREDIT_CARD" in violations[0]

    def test_detects_ipv4_pattern(self) -> None:
        """Test detection of IPv4 address pattern."""
        context = {"ip": "192.168.1.100"}
        is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii(context)
        assert is_valid is False
        assert len(violations) == 1
        assert "IPV4" in violations[0]

    def test_detects_ipv6_pattern(self) -> None:
        """Test detection of IPv6 address pattern."""
        context = {"ip": "2001:0db8:85a3:0000:0000:8a2e:0370:7334"}
        is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii(context)
        assert is_valid is False
        assert len(violations) == 1
        assert "IPV6" in violations[0]

    def test_detects_api_key_pattern(self) -> None:
        """Test detection of API key pattern."""
        # gitleaks:allow - intentional test fixture for PII detection testing
        context = {"key": "AKIAIOSFODNN7EXAMPLE"}
        is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii(context)
        assert is_valid is False
        assert len(violations) == 1
        assert "API_KEY" in violations[0]

    def test_ignores_uuid_by_default(self) -> None:
        """Test that UUIDs are NOT detected by default (check_uuids=False)."""
        context = {"workflow_id": "550e8400-e29b-41d4-a716-446655440000"}
        is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii(context)
        assert is_valid is True
        assert len(violations) == 0

    def test_detects_uuid_when_enabled(self) -> None:
        """Test that UUIDs are detected when check_uuids=True."""
        context = {"user_id": "550e8400-e29b-41d4-a716-446655440000"}
        is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii(
            context, check_uuids=True
        )
        assert is_valid is False
        assert len(violations) == 1
        assert "UUID" in violations[0]

    def test_returns_valid_for_clean_context(self) -> None:
        """Test that clean context passes validation."""
        context = {
            "status": "active",
            "count": 42,
            "enabled": True,
            "name": "test-workflow",
        }
        is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii(context)
        assert is_valid is True
        assert len(violations) == 0

    def test_detects_nested_pii(self) -> None:
        """Test detection of PII in nested structures."""
        context = {"user": {"profile": {"contact": {"email": "nested@example.com"}}}}
        is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii(context)
        assert is_valid is False
        assert len(violations) == 1
        assert "user.profile.contact.email" in violations[0]

    def test_detects_pii_in_list(self) -> None:
        """Test detection of PII in list values."""
        context = {"emails": ["user1@test.com", "user2@test.com"]}
        is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii(context)
        assert is_valid is False
        # Should detect both emails
        assert len(violations) == 2
        assert "emails[0]" in violations[0]
        assert "emails[1]" in violations[1]

    def test_reports_multiple_violations(self) -> None:
        """Test that multiple different PII types are all reported."""
        context = {
            "email": "user@test.com",
            "phone": "555-123-4567",
            "ip": "192.168.1.1",
        }
        is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii(context)
        assert is_valid is False
        assert len(violations) == 3

    def test_supports_custom_patterns(self) -> None:
        """Test that custom patterns can be added for validation."""
        context = {"token": "CUSTOM-secret-12345"}
        # Without custom pattern - should be valid
        is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii(context)
        assert is_valid is True

        # With custom pattern - should detect
        custom_patterns = [(r"CUSTOM-\w+-\d+", "CUSTOM_TOKEN")]
        is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii(
            context, additional_patterns=custom_patterns
        )
        assert is_valid is False
        assert "CUSTOM_TOKEN" in violations[0]

    def test_preserves_uuid_objects(self) -> None:
        """Test that UUID objects are not scanned (only strings are scanned)."""
        test_uuid = uuid4()
        context = {"workflow_id": test_uuid}
        # Even with check_uuids=True, UUID objects are not converted to strings
        # and scanned - only string values are checked
        is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii(
            context, check_uuids=True
        )
        assert is_valid is True
        assert len(violations) == 0

    def test_empty_context_is_valid(self) -> None:
        """Test that empty context passes validation."""
        is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii({})
        assert is_valid is True
        assert len(violations) == 0

    def test_only_reports_first_match_per_value(self) -> None:
        """Test that only the first PII pattern match is reported per value.

        This prevents redundant violations when a value matches multiple patterns.
        """
        # This value could match both CREDIT_CARD and PHONE patterns
        # but should only report one violation per value
        context = {"data": "Call me at 555-123-4567 or email me"}
        is_valid, violations = ModelWorkflowStateSnapshot.validate_no_pii(context)
        assert is_valid is False
        # Should report exactly one violation for this single value
        assert len(violations) == 1
