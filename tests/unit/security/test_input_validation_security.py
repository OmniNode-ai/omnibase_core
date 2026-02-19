# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Security test suite for input validation in PR #251 models.

This module provides comprehensive security tests for the typed payload models
introduced in PR #251. These tests verify that:

1. Injection attacks are properly rejected
2. UUID validation rejects malicious inputs
3. Validators don't expose sensitive information in error messages
4. Input sanitization works correctly

Test Categories:
    1. SQL Injection Attacks
    2. Script/XSS Injection Attacks
    3. Path Traversal Attacks
    4. Null Byte Injection
    5. Header Injection (CRLF)
    6. Error Message Sanitization
    7. Oversized Input Rejection
    8. Unicode Handling Security
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.context import (
    ModelCheckpointMetadata,
    ModelDetectionMetadata,
    ModelSessionContext,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Combined exception types for semver validation
# ModelOnexError is raised by ModelSemVer validators, ValidationError by Pydantic
SemVerValidationErrors = (ValidationError, ModelOnexError)


# =============================================================================
# SQL INJECTION ATTACK TESTS
# =============================================================================


@pytest.mark.unit
class TestSQLInjectionRejection:
    """Tests for SQL injection attack rejection."""

    SQL_INJECTION_PAYLOADS: list[str] = [
        "'; DROP TABLE users; --",
        "1; DELETE FROM sessions WHERE 1=1",
        "' OR '1'='1",
        "' UNION SELECT * FROM passwords --",
        "'; EXEC xp_cmdshell('dir'); --",
        "1' AND 1=CONVERT(int,(SELECT @@version))--",
        "admin'--",
        "' OR 1=1#",
        "') OR ('1'='1",
        "1; UPDATE users SET password='hacked'--",
    ]

    def test_session_id_rejects_sql_injection_payloads(self) -> None:
        """Test that session_id rejects all SQL injection payloads."""
        for payload in self.SQL_INJECTION_PAYLOADS:
            with pytest.raises(ValidationError):
                ModelSessionContext(session_id=payload)  # type: ignore[arg-type]

    def test_parent_checkpoint_id_rejects_sql_injection_payloads(self) -> None:
        """Test that parent_checkpoint_id rejects all SQL injection payloads."""
        for payload in self.SQL_INJECTION_PAYLOADS:
            with pytest.raises(ValidationError):
                ModelCheckpointMetadata(parent_checkpoint_id=payload)  # type: ignore[arg-type]

    def test_rule_version_rejects_sql_injection_payloads(self) -> None:
        """Test that rule_version rejects all SQL injection payloads."""
        for payload in self.SQL_INJECTION_PAYLOADS:
            with pytest.raises(SemVerValidationErrors):
                ModelDetectionMetadata(rule_version=payload)  # type: ignore[arg-type]


# =============================================================================
# SCRIPT/XSS INJECTION ATTACK TESTS
# =============================================================================


@pytest.mark.unit
class TestScriptInjectionRejection:
    """Tests for script/XSS injection attack rejection."""

    XSS_PAYLOADS: list[str] = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "<body onload=alert('XSS')>",
        "javascript:alert('XSS')",
        "<svg/onload=alert('XSS')>",
        "<iframe src='javascript:alert(1)'>",
        "'-alert(1)-'",
        '"onfocus=alert(1) autofocus="',
        "<marquee onstart=alert(1)>",
        "<details open ontoggle=alert(1)>",
    ]

    def test_session_id_rejects_xss_payloads(self) -> None:
        """Test that session_id rejects all XSS payloads."""
        for payload in self.XSS_PAYLOADS:
            with pytest.raises(ValidationError):
                ModelSessionContext(session_id=payload)  # type: ignore[arg-type]

    def test_parent_checkpoint_id_rejects_xss_payloads(self) -> None:
        """Test that parent_checkpoint_id rejects all XSS payloads."""
        for payload in self.XSS_PAYLOADS:
            with pytest.raises(ValidationError):
                ModelCheckpointMetadata(parent_checkpoint_id=payload)  # type: ignore[arg-type]

    def test_rule_version_rejects_xss_payloads(self) -> None:
        """Test that rule_version rejects all XSS payloads."""
        for payload in self.XSS_PAYLOADS:
            with pytest.raises(SemVerValidationErrors):
                ModelDetectionMetadata(rule_version=payload)  # type: ignore[arg-type]


# =============================================================================
# PATH TRAVERSAL ATTACK TESTS
# =============================================================================


@pytest.mark.unit
class TestPathTraversalRejection:
    """Tests for path traversal attack rejection."""

    PATH_TRAVERSAL_PAYLOADS: list[str] = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "/etc/shadow",
        "....//....//....//etc/passwd",
        "..%2F..%2F..%2Fetc%2Fpasswd",
        "..%252f..%252f..%252fetc%252fpasswd",
        "/var/log/../../../etc/passwd",
        "file:///etc/passwd",
        "\\\\server\\share\\file",
    ]

    def test_session_id_rejects_path_traversal(self) -> None:
        """Test that session_id rejects all path traversal payloads."""
        for payload in self.PATH_TRAVERSAL_PAYLOADS:
            with pytest.raises(ValidationError):
                ModelSessionContext(session_id=payload)  # type: ignore[arg-type]

    def test_parent_checkpoint_id_rejects_path_traversal(self) -> None:
        """Test that parent_checkpoint_id rejects all path traversal payloads."""
        for payload in self.PATH_TRAVERSAL_PAYLOADS:
            with pytest.raises(ValidationError):
                ModelCheckpointMetadata(parent_checkpoint_id=payload)  # type: ignore[arg-type]

    def test_rule_version_rejects_path_traversal(self) -> None:
        """Test that rule_version rejects all path traversal payloads."""
        for payload in self.PATH_TRAVERSAL_PAYLOADS:
            with pytest.raises(SemVerValidationErrors):
                ModelDetectionMetadata(rule_version=payload)  # type: ignore[arg-type]


# =============================================================================
# NULL BYTE INJECTION TESTS
# =============================================================================


@pytest.mark.unit
class TestNullByteInjectionRejection:
    """Tests for null byte injection rejection."""

    def test_session_id_rejects_null_byte_at_end(self) -> None:
        """Test that session_id rejects UUID with null byte at end."""
        with pytest.raises(ValidationError):
            ModelSessionContext(session_id="550e8400-e29b-41d4-a716-446655440000\x00")  # type: ignore[arg-type]

    def test_session_id_rejects_null_byte_in_middle(self) -> None:
        """Test that session_id rejects UUID with null byte in middle."""
        with pytest.raises(ValidationError):
            ModelSessionContext(session_id="550e8400-e29b\x00-41d4-a716-446655440000")  # type: ignore[arg-type]

    def test_session_id_rejects_null_byte_with_payload(self) -> None:
        """Test that session_id rejects valid UUID with null byte and payload."""
        with pytest.raises(ValidationError):
            ModelSessionContext(
                session_id="550e8400-e29b-41d4-a716-446655440000\x00malicious.exe"
            )  # type: ignore[arg-type]

    def test_client_ip_rejects_null_byte_injection(self) -> None:
        """Test that client_ip rejects IP with null byte."""
        with pytest.raises(ValidationError):
            ModelSessionContext(client_ip="192.168.1.1\x00")

    def test_rule_version_rejects_null_byte_injection(self) -> None:
        """Test that rule_version rejects version with null byte."""
        with pytest.raises(SemVerValidationErrors):
            ModelDetectionMetadata(rule_version="1.0.0\x00")  # type: ignore[arg-type]


# =============================================================================
# HEADER INJECTION (CRLF) TESTS
# =============================================================================


@pytest.mark.unit
class TestCRLFInjectionRejection:
    """Tests for CRLF (header) injection rejection."""

    CRLF_PAYLOADS: list[str] = [
        "value\r\nX-Injected: header",
        "value\nX-Injected: header",
        "value\rX-Injected: header",
        "value%0d%0aX-Injected: header",
        "value\r\n\r\n<html>injected</html>",
    ]

    def test_client_ip_rejects_crlf_injection(self) -> None:
        """Test that client_ip rejects CRLF injection payloads."""
        for payload in self.CRLF_PAYLOADS:
            with pytest.raises(ValidationError):
                ModelSessionContext(client_ip=payload)


# =============================================================================
# ERROR MESSAGE SANITIZATION TESTS
# =============================================================================


@pytest.mark.unit
class TestErrorMessageSanitization:
    """Tests to ensure error messages don't leak sensitive information."""

    def test_session_id_error_does_not_contain_traceback(self) -> None:
        """Test that session_id validation error doesn't expose traceback."""
        try:
            ModelSessionContext(session_id="secret-invalid-uuid")  # type: ignore[arg-type]
            pytest.fail("Should have raised ValidationError")
        except ValidationError as e:
            error_str = str(e)
            assert "Traceback" not in error_str
            assert "File" not in error_str or "test_" in error_str

    def test_session_id_error_provides_useful_guidance(self) -> None:
        """Test that session_id error provides useful field information."""
        try:
            ModelSessionContext(session_id="invalid")  # type: ignore[arg-type]
            pytest.fail("Should have raised ValidationError")
        except ValidationError as e:
            error_str = str(e).lower()
            # Should mention the field or type for user guidance
            assert "session_id" in error_str or "uuid" in error_str

    def test_client_ip_error_does_not_expose_internal_paths(self) -> None:
        """Test that client_ip error doesn't expose internal file paths."""
        try:
            ModelSessionContext(client_ip="invalid-ip")
            pytest.fail("Should have raised ValidationError")
        except ValidationError as e:
            error_str = str(e)
            # Should not expose internal implementation paths
            assert "/home/" not in error_str
            assert "/usr/" not in error_str
            assert "site-packages" not in error_str

    def test_rule_version_error_does_not_leak_stack_frames(self) -> None:
        """Test that rule_version error doesn't leak stack frame info."""
        try:
            ModelDetectionMetadata(rule_version="secret.version.string")  # type: ignore[arg-type]
            pytest.fail("Should have raised an error")
        except SemVerValidationErrors as e:
            error_str = str(e)
            # Should not contain memory addresses or object references
            assert "0x" not in error_str.lower()


# =============================================================================
# OVERSIZED INPUT REJECTION TESTS
# =============================================================================


@pytest.mark.unit
class TestOversizedInputRejection:
    """Tests for oversized input rejection."""

    def test_session_id_rejects_oversized_uuid_like_string(self) -> None:
        """Test that session_id rejects oversized UUID-like string."""
        oversized = "550e8400-e29b-41d4-a716-" + "0" * 10000
        with pytest.raises(ValidationError):
            ModelSessionContext(session_id=oversized)  # type: ignore[arg-type]

    def test_client_ip_rejects_oversized_input(self) -> None:
        """Test that client_ip rejects oversized input."""
        oversized = "1" * 10000
        with pytest.raises(ValidationError):
            ModelSessionContext(client_ip=oversized)

    def test_rule_version_rejects_oversized_string(self) -> None:
        """Test that rule_version rejects oversized string."""
        oversized = "1" * 10000 + ".0.0"
        with pytest.raises(SemVerValidationErrors):
            ModelDetectionMetadata(rule_version=oversized)  # type: ignore[arg-type]


# =============================================================================
# UNICODE SECURITY TESTS
# =============================================================================


@pytest.mark.unit
class TestUnicodeSecurity:
    """Tests for unicode handling security."""

    def test_session_id_rejects_unicode_lookalike_characters(self) -> None:
        """Test that session_id rejects unicode characters that look like hex."""
        # Cyrillic 'а' looks like Latin 'a' but is different
        with pytest.raises(ValidationError):
            ModelSessionContext(
                session_id="550е8400-е29b-41d4-а716-446655440000"  # noqa: RUF001 - Intentional Cyrillic chars for security test
            )  # type: ignore[arg-type]

    def test_client_ip_rejects_unicode_digits(self) -> None:
        """Test that client_ip rejects unicode digit lookalikes.

        Note: This is a documentation test - Python's ipaddress library
        correctly handles unicode by rejecting non-ASCII digits.
        The fullwidth numbers (e.g., 1 = U+FF11) would be rejected.
        """
        # Fullwidth digits look similar to ASCII digits but are different
        # 1 = U+FF11 (fullwidth digit one)
        fullwidth_ip = "\uff11\uff19\uff12.168.1.1"
        with pytest.raises(ValidationError):
            ModelSessionContext(client_ip=fullwidth_ip)

    def test_user_agent_accepts_legitimate_unicode(self) -> None:
        """Test that user_agent accepts legitimate unicode content."""
        # This should be accepted - it's a legitimate use case
        context = ModelSessionContext(
            user_agent="Mozilla/5.0 (Compatible; 日本語ブラウザ/1.0)"
        )
        assert context.user_agent is not None
        assert "日本語" in context.user_agent

    def test_string_fields_handle_rtl_characters(self) -> None:
        """Test that string fields handle RTL (Arabic/Hebrew) characters safely."""
        # RTL characters shouldn't cause issues
        metadata = ModelDetectionMetadata(
            pattern_category="test_pattern_العربية",
            remediation_hint="Fix issue: עברית guidance",
        )
        assert "العربية" in metadata.pattern_category  # type: ignore[operator]
        assert "עברית" in metadata.remediation_hint  # type: ignore[operator]

    def test_string_fields_handle_mixed_direction_text(self) -> None:
        """Test that string fields handle mixed LTR/RTL text safely."""
        metadata = ModelDetectionMetadata(
            pattern_category="English العربية Hebrew עברית mixed"
        )
        assert "English" in metadata.pattern_category  # type: ignore[operator]
        assert "العربية" in metadata.pattern_category  # type: ignore[operator]
        assert "עברית" in metadata.pattern_category  # type: ignore[operator]


# =============================================================================
# TYPE CONFUSION TESTS
# =============================================================================


@pytest.mark.unit
class TestTypeConfusionRejection:
    """Tests for type confusion attack rejection."""

    def test_session_id_rejects_dict_type(self) -> None:
        """Test that session_id rejects dict input."""
        with pytest.raises(ValidationError):
            ModelSessionContext(
                session_id={"uuid": "550e8400-e29b-41d4-a716-446655440000"}
            )  # type: ignore[arg-type]

    def test_session_id_rejects_list_type(self) -> None:
        """Test that session_id rejects list input."""
        with pytest.raises(ValidationError):
            ModelSessionContext(session_id=["550e8400-e29b-41d4-a716-446655440000"])  # type: ignore[arg-type]

    def test_session_id_rejects_boolean_type(self) -> None:
        """Test that session_id rejects boolean input."""
        with pytest.raises(ValidationError):
            ModelSessionContext(session_id=True)  # type: ignore[arg-type]

    def test_session_id_rejects_float_type(self) -> None:
        """Test that session_id rejects float input."""
        with pytest.raises(ValidationError):
            ModelSessionContext(session_id=3.14159)  # type: ignore[arg-type]

    def test_rule_version_rejects_nested_dict(self) -> None:
        """Test that rule_version rejects nested dict input."""
        with pytest.raises(SemVerValidationErrors):
            ModelDetectionMetadata(
                rule_version={"major": {"value": 1}, "minor": 0, "patch": 0}  # type: ignore[arg-type]
            )

    def test_rule_version_rejects_list_of_numbers(self) -> None:
        """Test that rule_version rejects list of numbers."""
        with pytest.raises(SemVerValidationErrors):
            ModelDetectionMetadata(rule_version=[1, 2, 3])  # type: ignore[arg-type]


# =============================================================================
# BOUNDARY CONDITION TESTS
# =============================================================================


@pytest.mark.unit
class TestBoundaryConditions:
    """Tests for boundary conditions and edge cases."""

    def test_empty_string_uuid_rejected(self) -> None:
        """Test that empty string is rejected for UUID fields."""
        with pytest.raises(ValidationError):
            ModelSessionContext(session_id="")  # type: ignore[arg-type]

    def test_whitespace_only_uuid_rejected(self) -> None:
        """Test that whitespace-only string is rejected for UUID fields."""
        with pytest.raises(ValidationError):
            ModelSessionContext(session_id="   ")  # type: ignore[arg-type]

    def test_newline_only_uuid_rejected(self) -> None:
        """Test that newline-only string is rejected for UUID fields."""
        with pytest.raises(ValidationError):
            ModelSessionContext(session_id="\n")  # type: ignore[arg-type]

    def test_empty_string_ip_rejected(self) -> None:
        """Test that empty string is rejected for IP fields."""
        with pytest.raises(ValidationError):
            ModelSessionContext(client_ip="")

    def test_whitespace_only_ip_rejected(self) -> None:
        """Test that whitespace-only string is rejected for IP fields."""
        with pytest.raises(ValidationError):
            ModelSessionContext(client_ip="   ")

    def test_valid_uuid_with_surrounding_whitespace(self) -> None:
        """Test UUID with surrounding whitespace behavior."""
        # Depending on implementation, this may be accepted or rejected
        uuid_with_spaces = "  550e8400-e29b-41d4-a716-446655440000  "
        with pytest.raises(ValidationError):
            # Should be rejected - whitespace makes it invalid
            ModelSessionContext(session_id=uuid_with_spaces)  # type: ignore[arg-type]

    def test_valid_ip_with_surrounding_whitespace(self) -> None:
        """Test IP with surrounding whitespace behavior."""
        ip_with_spaces = "  192.168.1.1  "
        with pytest.raises(ValidationError):
            # Should be rejected - whitespace makes it invalid
            ModelSessionContext(client_ip=ip_with_spaces)
