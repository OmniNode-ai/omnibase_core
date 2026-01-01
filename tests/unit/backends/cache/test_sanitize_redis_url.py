# Copyright (c) 2025 OmniNode Team. All rights reserved.
"""Tests for Redis URL sanitization.

This module tests the sanitize_redis_url and sanitize_error_message functions
to ensure they properly remove credentials from Redis URLs before logging.

Related:
    - OMN-1188: Redis/Valkey L2 backend security
    - PR #301: Security fix for credential leakage
"""

from __future__ import annotations

import pytest

from omnibase_core.backends.cache import sanitize_error_message, sanitize_redis_url


@pytest.mark.unit
class TestSanitizeRedisUrl:
    """Tests for sanitize_redis_url function."""

    @pytest.mark.timeout(60)
    def test_url_without_password_unchanged(self) -> None:
        """URLs without passwords should remain unchanged."""
        url = "redis://localhost:6379/0"
        assert sanitize_redis_url(url) == url

    @pytest.mark.timeout(60)
    def test_url_with_password_only(self) -> None:
        """URLs with password only (no username) should mask password."""
        url = "redis://:secretpassword@localhost:6379/0"
        result = sanitize_redis_url(url)
        assert result == "redis://:***@localhost:6379/0"
        assert "secretpassword" not in result

    @pytest.mark.timeout(60)
    def test_url_with_username_and_password(self) -> None:
        """URLs with username and password should mask only password."""
        url = "redis://user:secretpassword@localhost:6379/0"
        result = sanitize_redis_url(url)
        assert result == "redis://user:***@localhost:6379/0"
        assert "secretpassword" not in result
        assert "user" in result

    @pytest.mark.timeout(60)
    def test_url_with_non_standard_port(self) -> None:
        """URLs with non-standard ports should preserve port."""
        url = "redis://:password@myhost:16379/2"
        result = sanitize_redis_url(url)
        assert result == "redis://:***@myhost:16379/2"
        assert "16379" in result
        assert "password" not in result

    @pytest.mark.timeout(60)
    def test_rediss_scheme(self) -> None:
        """TLS URLs (rediss://) should be handled correctly."""
        url = "rediss://user:pass@secure.redis.io:6379/0"
        result = sanitize_redis_url(url)
        assert result == "rediss://user:***@secure.redis.io:6379/0"
        assert "pass" not in result
        assert result.startswith("rediss://")

    @pytest.mark.timeout(60)
    def test_empty_url(self) -> None:
        """Empty URLs should return safe fallback."""
        result = sanitize_redis_url("")
        # Empty URLs have no password, so return as-is
        assert result == ""

    @pytest.mark.timeout(60)
    def test_invalid_url_returns_safe_string(self) -> None:
        """Invalid URLs that cannot be parsed should return safe fallback."""
        # Test with a URL that might cause parsing issues
        result = sanitize_redis_url("not://a[valid:url")
        # Should not contain credentials or raise exceptions
        assert isinstance(result, str)

    @pytest.mark.timeout(60)
    def test_url_preserves_database_number(self) -> None:
        """Database number in URL path should be preserved."""
        url = "redis://:secret@localhost:6379/5"
        result = sanitize_redis_url(url)
        assert result == "redis://:***@localhost:6379/5"
        assert "/5" in result

    @pytest.mark.timeout(60)
    def test_url_without_port(self) -> None:
        """URLs without explicit port should work correctly."""
        url = "redis://user:pass@localhost/0"
        result = sanitize_redis_url(url)
        # Port should not be included if not in original
        assert "pass" not in result
        assert "user" in result

    @pytest.mark.timeout(60)
    def test_long_password_fully_masked(self) -> None:
        """Long passwords should be fully masked."""
        long_pass = "a" * 100
        url = f"redis://:{long_pass}@localhost:6379/0"
        result = sanitize_redis_url(url)
        assert long_pass not in result
        assert "***" in result

    @pytest.mark.timeout(60)
    def test_special_characters_in_password(self) -> None:
        """Passwords with special characters should be handled."""
        # URL-encoded password with special chars
        url = "redis://:p%40ss%23word@localhost:6379/0"
        result = sanitize_redis_url(url)
        assert "p%40ss%23word" not in result
        assert "***" in result


@pytest.mark.unit
class TestSanitizeRedisUrlEdgeCases:
    """Edge case tests for sanitize_redis_url."""

    @pytest.mark.timeout(60)
    def test_url_with_only_host(self) -> None:
        """Minimal URL with only host should work."""
        url = "redis://localhost"
        result = sanitize_redis_url(url)
        assert result == url

    @pytest.mark.timeout(60)
    def test_none_like_values_in_parsing(self) -> None:
        """URL parsing edge cases should not crash."""
        # URL with @ but no password
        url = "redis://@localhost:6379/0"
        result = sanitize_redis_url(url)
        assert isinstance(result, str)
        # Should not raise exceptions


@pytest.mark.unit
class TestSanitizeErrorMessage:
    """Tests for sanitize_error_message function.

    This function is used to sanitize exception messages that may contain
    Redis URLs with credentials, preventing credential leakage in logs.
    """

    @pytest.mark.timeout(60)
    def test_message_without_url_unchanged(self) -> None:
        """Messages without Redis URLs should remain unchanged."""
        message = "Connection refused"
        assert sanitize_error_message(message) == message

    @pytest.mark.timeout(60)
    def test_message_with_password_only_url(self) -> None:
        """Messages containing URLs with password only should be sanitized."""
        message = "Error connecting to redis://:secretpassword@localhost:6379/0"
        result = sanitize_error_message(message)
        assert "secretpassword" not in result
        assert "***" in result
        assert "Error connecting to" in result

    @pytest.mark.timeout(60)
    def test_message_with_username_and_password(self) -> None:
        """Messages with username:password URLs should mask only password."""
        message = "Failed: redis://admin:supersecret@host:6379/0 unreachable"
        result = sanitize_error_message(message)
        assert "supersecret" not in result
        assert "admin:***@" in result
        assert "unreachable" in result

    @pytest.mark.timeout(60)
    def test_message_with_multiple_urls(self) -> None:
        """Messages with multiple Redis URLs should sanitize all of them."""
        message = (
            "Primary redis://:pass1@host1:6379 failed, "
            "fallback redis://user:pass2@host2:6380 also failed"
        )
        result = sanitize_error_message(message)
        assert "pass1" not in result
        assert "pass2" not in result
        assert "host1" in result
        assert "host2" in result

    @pytest.mark.timeout(60)
    def test_message_with_rediss_url(self) -> None:
        """Messages with TLS URLs (rediss://) should be sanitized."""
        message = (
            "TLS connection to rediss://admin:secret@secure.redis.io:6379/0 failed"
        )
        result = sanitize_error_message(message)
        assert "secret" not in result
        assert "admin:***@" in result
        assert "rediss://" in result

    @pytest.mark.timeout(60)
    def test_message_with_url_no_credentials(self) -> None:
        """Messages with URLs without credentials should remain unchanged."""
        message = "Connected to redis://localhost:6379/0 successfully"
        result = sanitize_error_message(message)
        assert result == message

    @pytest.mark.timeout(60)
    def test_empty_message(self) -> None:
        """Empty messages should return empty string."""
        assert sanitize_error_message("") == ""

    @pytest.mark.timeout(60)
    def test_redis_exception_format(self) -> None:
        """Test format similar to actual Redis exception messages."""
        # Simulate a Redis library exception message
        message = "Error 111 connecting to redis://:MySecretPass@192.168.1.1:6379. Connection refused."
        result = sanitize_error_message(message)
        assert "MySecretPass" not in result
        assert ":***@" in result
        assert "192.168.1.1:6379" in result
        assert "Connection refused" in result

    @pytest.mark.timeout(60)
    def test_preserves_database_number(self) -> None:
        """Database number in URL should be preserved after sanitization."""
        message = "Error on redis://:secret@host:6379/5"
        result = sanitize_error_message(message)
        assert "secret" not in result
        assert "/5" in result

    @pytest.mark.timeout(60)
    def test_complex_password_characters(self) -> None:
        """Passwords with special characters should be fully masked."""
        message = "Error: redis://user:p@ss:word!@host:6379"
        result = sanitize_error_message(message)
        # The password should not appear in output
        assert "p@ss:word!" not in result
        assert "user:***@" in result
