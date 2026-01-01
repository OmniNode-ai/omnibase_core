# Copyright (c) 2025 OmniNode Team. All rights reserved.
"""Tests for Redis URL sanitization.

This module tests the sanitize_redis_url function to ensure it properly
removes credentials from Redis URLs before logging.

Related:
    - OMN-1188: Redis/Valkey L2 backend security
    - PR #301: Security fix for credential leakage
"""

from __future__ import annotations

import pytest

from omnibase_core.backends.cache import sanitize_redis_url


class TestSanitizeRedisUrl:
    """Tests for sanitize_redis_url function."""

    def test_url_without_password_unchanged(self) -> None:
        """URLs without passwords should remain unchanged."""
        url = "redis://localhost:6379/0"
        assert sanitize_redis_url(url) == url

    def test_url_with_password_only(self) -> None:
        """URLs with password only (no username) should mask password."""
        url = "redis://:secretpassword@localhost:6379/0"
        result = sanitize_redis_url(url)
        assert result == "redis://:***@localhost:6379/0"
        assert "secretpassword" not in result

    def test_url_with_username_and_password(self) -> None:
        """URLs with username and password should mask only password."""
        url = "redis://user:secretpassword@localhost:6379/0"
        result = sanitize_redis_url(url)
        assert result == "redis://user:***@localhost:6379/0"
        assert "secretpassword" not in result
        assert "user" in result

    def test_url_with_non_standard_port(self) -> None:
        """URLs with non-standard ports should preserve port."""
        url = "redis://:password@myhost:16379/2"
        result = sanitize_redis_url(url)
        assert result == "redis://:***@myhost:16379/2"
        assert "16379" in result
        assert "password" not in result

    def test_rediss_scheme(self) -> None:
        """TLS URLs (rediss://) should be handled correctly."""
        url = "rediss://user:pass@secure.redis.io:6379/0"
        result = sanitize_redis_url(url)
        assert result == "rediss://user:***@secure.redis.io:6379/0"
        assert "pass" not in result
        assert result.startswith("rediss://")

    def test_empty_url(self) -> None:
        """Empty URLs should return safe fallback."""
        result = sanitize_redis_url("")
        # Empty URLs have no password, so return as-is
        assert result == ""

    def test_invalid_url_returns_safe_string(self) -> None:
        """Invalid URLs that cannot be parsed should return safe fallback."""
        # Test with a URL that might cause parsing issues
        result = sanitize_redis_url("not://a[valid:url")
        # Should not contain credentials or raise exceptions
        assert isinstance(result, str)

    def test_url_preserves_database_number(self) -> None:
        """Database number in URL path should be preserved."""
        url = "redis://:secret@localhost:6379/5"
        result = sanitize_redis_url(url)
        assert result == "redis://:***@localhost:6379/5"
        assert "/5" in result

    def test_url_without_port(self) -> None:
        """URLs without explicit port should work correctly."""
        url = "redis://user:pass@localhost/0"
        result = sanitize_redis_url(url)
        # Port should not be included if not in original
        assert "pass" not in result
        assert "user" in result

    def test_long_password_fully_masked(self) -> None:
        """Long passwords should be fully masked."""
        long_pass = "a" * 100
        url = f"redis://:{long_pass}@localhost:6379/0"
        result = sanitize_redis_url(url)
        assert long_pass not in result
        assert "***" in result

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

    def test_url_with_only_host(self) -> None:
        """Minimal URL with only host should work."""
        url = "redis://localhost"
        result = sanitize_redis_url(url)
        assert result == url

    def test_none_like_values_in_parsing(self) -> None:
        """URL parsing edge cases should not crash."""
        # URL with @ but no password
        url = "redis://@localhost:6379/0"
        result = sanitize_redis_url(url)
        assert isinstance(result, str)
        # Should not raise exceptions
