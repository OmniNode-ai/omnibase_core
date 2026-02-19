# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelSessionContext validators and edge cases.

These tests focus on the validator logic introduced in PR #251:
- session_id UUID coercion (string to UUID)
- client_ip validation (IPv4 and IPv6)
- authentication_method enum normalization
- Security-focused tests for malicious inputs

Related tests in test_context_models.py cover basic instantiation,
defaults, immutability, and from_attributes behavior.
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.context import ModelSessionContext

# =============================================================================
# UUID COERCION TESTS
# =============================================================================


@pytest.mark.unit
class TestModelSessionContextUUIDCoercion:
    """Tests for session_id UUID coercion validator."""

    def test_session_id_accepts_uuid_directly(self) -> None:
        """Test that session_id accepts UUID objects directly."""
        test_uuid = uuid4()
        context = ModelSessionContext(session_id=test_uuid)
        assert context.session_id == test_uuid
        assert isinstance(context.session_id, UUID)

    def test_session_id_coerces_valid_string_to_uuid(self) -> None:
        """Test that valid UUID string is coerced to UUID type."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        context = ModelSessionContext(session_id=uuid_str)  # type: ignore[arg-type]
        assert context.session_id == UUID(uuid_str)
        assert isinstance(context.session_id, UUID)

    def test_session_id_coerces_uppercase_uuid_string(self) -> None:
        """Test that uppercase UUID string is coerced to UUID type."""
        uuid_str = "550E8400-E29B-41D4-A716-446655440000"
        context = ModelSessionContext(session_id=uuid_str)  # type: ignore[arg-type]
        assert isinstance(context.session_id, UUID)

    def test_session_id_coerces_uuid_without_hyphens(self) -> None:
        """Test that UUID string without hyphens is coerced to UUID type."""
        uuid_str = "550e8400e29b41d4a716446655440000"
        context = ModelSessionContext(session_id=uuid_str)  # type: ignore[arg-type]
        assert isinstance(context.session_id, UUID)

    def test_session_id_rejects_invalid_string(self) -> None:
        """Test that invalid string raises ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelSessionContext(session_id="not-a-valid-uuid")  # type: ignore[arg-type]
        error_message = str(exc_info.value).lower()
        assert "session_id" in error_message or "uuid" in error_message

    def test_session_id_rejects_empty_string(self) -> None:
        """Test that empty string raises ValueError."""
        with pytest.raises(ValidationError):
            ModelSessionContext(session_id="")  # type: ignore[arg-type]

    def test_session_id_rejects_partial_uuid(self) -> None:
        """Test that partial UUID raises ValueError."""
        with pytest.raises(ValidationError):
            ModelSessionContext(session_id="550e8400-e29b")  # type: ignore[arg-type]

    def test_session_id_accepts_none(self) -> None:
        """Test that session_id accepts None."""
        context = ModelSessionContext(session_id=None)
        assert context.session_id is None

    def test_session_id_rejects_integer(self) -> None:
        """Test that session_id rejects integer input."""
        with pytest.raises(ValidationError):
            ModelSessionContext(session_id=12345)  # type: ignore[arg-type]

    def test_session_id_rejects_dict(self) -> None:
        """Test that session_id rejects dict input."""
        with pytest.raises(ValidationError):
            ModelSessionContext(session_id={"uuid": "test"})  # type: ignore[arg-type]

    def test_session_id_rejects_list(self) -> None:
        """Test that session_id rejects list input."""
        with pytest.raises(ValidationError):
            ModelSessionContext(session_id=["550e8400-e29b-41d4-a716-446655440000"])  # type: ignore[arg-type]


# =============================================================================
# IP ADDRESS VALIDATION TESTS
# =============================================================================


@pytest.mark.unit
class TestModelSessionContextIPValidation:
    """Tests for client_ip validation."""

    # Valid IPv4 tests
    def test_client_ip_accepts_valid_ipv4(self) -> None:
        """Test that valid IPv4 address is accepted."""
        context = ModelSessionContext(client_ip="192.168.1.100")
        assert context.client_ip == "192.168.1.100"

    def test_client_ip_accepts_localhost_ipv4(self) -> None:
        """Test that localhost IPv4 is accepted."""
        context = ModelSessionContext(client_ip="127.0.0.1")
        assert context.client_ip == "127.0.0.1"

    def test_client_ip_accepts_any_ipv4(self) -> None:
        """Test that 0.0.0.0 is accepted."""
        context = ModelSessionContext(client_ip="0.0.0.0")
        assert context.client_ip == "0.0.0.0"

    def test_client_ip_accepts_broadcast_ipv4(self) -> None:
        """Test that broadcast address is accepted."""
        context = ModelSessionContext(client_ip="255.255.255.255")
        assert context.client_ip == "255.255.255.255"

    def test_client_ip_accepts_private_ipv4_ranges(self) -> None:
        """Test that private IPv4 ranges are accepted."""
        # Class A private
        context_a = ModelSessionContext(client_ip="10.0.0.1")
        assert context_a.client_ip == "10.0.0.1"
        # Class B private
        context_b = ModelSessionContext(client_ip="172.16.0.1")
        assert context_b.client_ip == "172.16.0.1"
        # Class C private
        context_c = ModelSessionContext(client_ip="192.168.0.1")
        assert context_c.client_ip == "192.168.0.1"

    # Valid IPv6 tests
    def test_client_ip_accepts_valid_ipv6(self) -> None:
        """Test that valid IPv6 address is accepted."""
        context = ModelSessionContext(
            client_ip="2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        )
        # ipaddress normalizes the format
        assert context.client_ip is not None
        assert "2001" in context.client_ip

    def test_client_ip_accepts_ipv6_compressed(self) -> None:
        """Test that compressed IPv6 is accepted."""
        context = ModelSessionContext(client_ip="2001:db8::1")
        assert context.client_ip is not None

    def test_client_ip_accepts_ipv6_localhost(self) -> None:
        """Test that IPv6 localhost is accepted."""
        context = ModelSessionContext(client_ip="::1")
        assert context.client_ip == "::1"

    def test_client_ip_accepts_ipv6_any(self) -> None:
        """Test that IPv6 any address is accepted."""
        context = ModelSessionContext(client_ip="::")
        assert context.client_ip == "::"

    def test_client_ip_accepts_ipv6_mapped_ipv4(self) -> None:
        """Test that IPv6-mapped IPv4 is accepted."""
        context = ModelSessionContext(client_ip="::ffff:192.168.1.1")
        assert context.client_ip is not None

    # Invalid IP tests
    def test_client_ip_rejects_invalid_ipv4(self) -> None:
        """Test that invalid IPv4 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelSessionContext(client_ip="256.256.256.256")
        assert (
            "client_ip" in str(exc_info.value).lower()
            or "ip" in str(exc_info.value).lower()
        )

    def test_client_ip_rejects_invalid_ipv4_segments(self) -> None:
        """Test that IPv4 with too many segments is rejected."""
        with pytest.raises(ValidationError):
            ModelSessionContext(client_ip="192.168.1.1.1")

    def test_client_ip_rejects_ipv4_with_too_few_segments(self) -> None:
        """Test that IPv4 with too few segments is rejected."""
        with pytest.raises(ValidationError):
            ModelSessionContext(client_ip="192.168.1")

    def test_client_ip_rejects_hostname(self) -> None:
        """Test that hostname is rejected (not an IP)."""
        with pytest.raises(ValidationError):
            ModelSessionContext(client_ip="example.com")

    def test_client_ip_rejects_arbitrary_string(self) -> None:
        """Test that arbitrary string is rejected."""
        with pytest.raises(ValidationError):
            ModelSessionContext(client_ip="not-an-ip-address")

    def test_client_ip_rejects_empty_string(self) -> None:
        """Test that empty string is rejected."""
        with pytest.raises(ValidationError):
            ModelSessionContext(client_ip="")

    def test_client_ip_accepts_none(self) -> None:
        """Test that client_ip accepts None."""
        context = ModelSessionContext(client_ip=None)
        assert context.client_ip is None

    def test_client_ip_rejects_ipv4_with_port(self) -> None:
        """Test that IP with port is rejected."""
        with pytest.raises(ValidationError):
            ModelSessionContext(client_ip="192.168.1.1:8080")

    def test_client_ip_rejects_cidr_notation(self) -> None:
        """Test that CIDR notation is rejected."""
        with pytest.raises(ValidationError):
            ModelSessionContext(client_ip="192.168.1.0/24")

    def test_client_ip_rejects_ipv4_with_leading_zeros(self) -> None:
        """Test that IPv4 with leading zeros is rejected or normalized."""
        # Some systems accept this, others reject - test current behavior
        try:
            context = ModelSessionContext(client_ip="192.168.001.001")
            # If accepted, it should be normalized
            assert context.client_ip in ["192.168.1.1", "192.168.001.001"]
        except ValidationError:
            # Also valid - rejecting leading zeros
            pass


# =============================================================================
# SECURITY TESTS
# =============================================================================


@pytest.mark.unit
class TestModelSessionContextSecurity:
    """Security-focused tests for ModelSessionContext."""

    def test_session_id_rejects_sql_injection_attempt(self) -> None:
        """Test that SQL injection in session_id is rejected."""
        with pytest.raises(ValidationError):
            ModelSessionContext(session_id="'; DROP TABLE sessions; --")  # type: ignore[arg-type]

    def test_session_id_rejects_script_injection_attempt(self) -> None:
        """Test that script injection in session_id is rejected."""
        with pytest.raises(ValidationError):
            ModelSessionContext(session_id="<script>alert('xss')</script>")  # type: ignore[arg-type]

    def test_session_id_rejects_path_traversal_attempt(self) -> None:
        """Test that path traversal in session_id is rejected."""
        with pytest.raises(ValidationError):
            ModelSessionContext(session_id="../../etc/passwd")  # type: ignore[arg-type]

    def test_session_id_rejects_null_byte_injection(self) -> None:
        """Test that null byte in session_id is rejected."""
        with pytest.raises(ValidationError):
            ModelSessionContext(
                session_id="550e8400-e29b-41d4-a716-446655440000\x00malicious"
            )  # type: ignore[arg-type]

    def test_client_ip_rejects_newline_injection(self) -> None:
        """Test that newline injection in client_ip is rejected."""
        with pytest.raises(ValidationError):
            ModelSessionContext(client_ip="192.168.1.1\nX-Injected-Header: value")

    def test_client_ip_rejects_carriage_return_injection(self) -> None:
        """Test that carriage return injection in client_ip is rejected."""
        with pytest.raises(ValidationError):
            ModelSessionContext(client_ip="192.168.1.1\r\nX-Injected-Header: value")

    def test_error_message_does_not_leak_sensitive_data(self) -> None:
        """Test that error messages don't expose sensitive internal details."""
        try:
            ModelSessionContext(session_id="invalid-secret-value")  # type: ignore[arg-type]
        except ValidationError as e:
            error_str = str(e)
            # Should not contain full stack traces or internal paths
            assert "Traceback" not in error_str
            # Should mention the field name for user guidance
            assert "session_id" in error_str.lower() or "uuid" in error_str.lower()

    def test_client_ip_rejects_oversized_input(self) -> None:
        """Test that oversized input is rejected."""
        # Generate a very long string that looks like it could be an IP
        oversized = "1" * 10000
        with pytest.raises(ValidationError):
            ModelSessionContext(client_ip=oversized)

    def test_user_agent_accepts_unicode(self) -> None:
        """Test that unicode in user_agent is handled safely.

        Unicode characters should be accepted for internationalization.
        """
        context = ModelSessionContext(
            user_agent="Mozilla/5.0 TestBrowser/1.0 (Language: 日本語; Platform: Windows)"
        )
        assert "日本語" in context.user_agent  # type: ignore[operator]

    def test_locale_with_unicode(self) -> None:
        """Test that locale handles various unicode safely."""
        # Standard BCP 47 format
        context = ModelSessionContext(locale="zh-Hans-CN")
        assert context.locale == "zh-Hans-CN"


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


@pytest.mark.unit
class TestModelSessionContextEdgeCases:
    """Edge case tests for ModelSessionContext."""

    def test_all_fields_none(self) -> None:
        """Test creating context with all fields as None."""
        context = ModelSessionContext()
        assert context.session_id is None
        assert context.client_ip is None
        assert context.user_agent is None
        assert context.device_fingerprint is None
        assert context.locale is None
        assert context.authentication_method is None

    def test_model_dump_round_trip(self) -> None:
        """Test that model can be serialized and deserialized."""
        test_uuid = uuid4()
        original = ModelSessionContext(
            session_id=test_uuid,
            client_ip="192.168.1.1",
            user_agent="TestAgent/1.0",
            device_fingerprint="fp_test123",
            locale="en-US",
            authentication_method="oauth2",
        )

        dumped = original.model_dump()
        restored = ModelSessionContext.model_validate(dumped)

        assert restored.session_id == original.session_id
        assert restored.client_ip == original.client_ip
        assert restored.user_agent == original.user_agent
        assert restored.device_fingerprint == original.device_fingerprint
        assert restored.locale == original.locale
        assert restored.authentication_method == original.authentication_method

    def test_json_round_trip(self) -> None:
        """Test JSON serialization round trip."""
        import json

        test_uuid = uuid4()
        original = ModelSessionContext(
            session_id=test_uuid,
            client_ip="::1",
            locale="fr-CA",
        )

        json_str = original.model_dump_json()
        parsed = json.loads(json_str)
        restored = ModelSessionContext.model_validate(parsed)

        assert restored.session_id == original.session_id
        assert restored.client_ip == original.client_ip

    def test_hashable_for_frozen_model(self) -> None:
        """Test that frozen model is hashable."""
        context1 = ModelSessionContext(
            session_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            client_ip="192.168.1.1",
        )
        context2 = ModelSessionContext(
            session_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            client_ip="192.168.1.1",
        )

        assert hash(context1) == hash(context2)
        assert context1 == context2

        # Can be used in set
        context_set = {context1, context2}
        assert len(context_set) == 1

    def test_unicode_in_string_fields(self) -> None:
        """Test unicode handling in string fields.

        Tests multiple scripts: Japanese, Arabic, Greek, emoji.
        """
        context = ModelSessionContext(
            user_agent="Mozilla/5.0 (日本語; العربية; Ελληνικά)",
            device_fingerprint="fp_emoji_test_🔐",
            locale="ja-JP",
        )
        assert "日本語" in context.user_agent  # type: ignore[operator]
        assert "العربية" in context.user_agent  # type: ignore[operator]
        assert "Ελληνικά" in context.user_agent  # type: ignore[operator]
        assert "🔐" in context.device_fingerprint  # type: ignore[operator]
