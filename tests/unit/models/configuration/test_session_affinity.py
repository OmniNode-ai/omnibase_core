# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelSessionAffinity hash algorithm validation.

These tests verify that:
1. MD5 and SHA-1 are REJECTED (not allowed due to cryptographic weaknesses)
2. SHA-256, SHA-384, and SHA-512 are accepted
3. Hash calculation produces consistent results
4. Default algorithm is sha256

Security Note: MD5 and SHA-1 support was removed due to known cryptographic
weaknesses. Only SHA-256 or stronger algorithms are allowed.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.configuration.model_session_affinity import (
    ModelSessionAffinity,
)


@pytest.mark.unit
class TestSessionAffinityHashAlgorithm:
    """Tests for hash algorithm field validation."""

    def test_md5_rejected(self) -> None:
        """MD5 should be rejected due to cryptographic weakness."""
        with pytest.raises(ValidationError) as exc_info:
            ModelSessionAffinity(hash_algorithm="md5")

        # Verify the error mentions the pattern constraint
        error_str = str(exc_info.value)
        assert "hash_algorithm" in error_str

    def test_sha1_rejected(self) -> None:
        """SHA-1 should be rejected due to cryptographic weakness."""
        with pytest.raises(ValidationError) as exc_info:
            ModelSessionAffinity(hash_algorithm="sha1")

        # Verify the error mentions the pattern constraint
        error_str = str(exc_info.value)
        assert "hash_algorithm" in error_str

    def test_sha256_accepted(self) -> None:
        """SHA-256 should be accepted."""
        affinity = ModelSessionAffinity(hash_algorithm="sha256")
        assert affinity.hash_algorithm == "sha256"

    def test_sha384_accepted(self) -> None:
        """SHA-384 should be accepted."""
        affinity = ModelSessionAffinity(hash_algorithm="sha384")
        assert affinity.hash_algorithm == "sha384"

    def test_sha512_accepted(self) -> None:
        """SHA-512 should be accepted."""
        affinity = ModelSessionAffinity(hash_algorithm="sha512")
        assert affinity.hash_algorithm == "sha512"

    def test_default_algorithm_is_sha256(self) -> None:
        """Default hash algorithm should be sha256."""
        affinity = ModelSessionAffinity()
        assert affinity.hash_algorithm == "sha256"

    def test_invalid_algorithm_rejected(self) -> None:
        """Arbitrary invalid algorithms should be rejected."""
        with pytest.raises(ValidationError):
            ModelSessionAffinity(hash_algorithm="invalid")
        with pytest.raises(ValidationError):
            ModelSessionAffinity(hash_algorithm="")
        with pytest.raises(ValidationError):
            ModelSessionAffinity(hash_algorithm="SHA256")  # Case sensitive


@pytest.mark.unit
class TestSessionAffinityHashCalculation:
    """Tests for hash calculation functionality."""

    def test_calculate_node_hash_sha256(self) -> None:
        """SHA-256 hash calculation should return consistent results."""
        affinity = ModelSessionAffinity(enabled=True, hash_algorithm="sha256")
        nodes = ["node1", "node2", "node3"]

        result1 = affinity.calculate_node_hash("test_key", nodes)
        result2 = affinity.calculate_node_hash("test_key", nodes)

        assert result1 is not None
        assert result1 == result2  # Consistent results
        assert result1 in nodes

    def test_calculate_node_hash_sha384(self) -> None:
        """SHA-384 hash calculation should work correctly."""
        affinity = ModelSessionAffinity(enabled=True, hash_algorithm="sha384")
        nodes = ["node1", "node2", "node3"]

        result = affinity.calculate_node_hash("test_key", nodes)

        assert result is not None
        assert result in nodes

    def test_calculate_node_hash_sha512(self) -> None:
        """SHA-512 hash calculation should work correctly."""
        affinity = ModelSessionAffinity(enabled=True, hash_algorithm="sha512")
        nodes = ["node1", "node2", "node3"]

        result = affinity.calculate_node_hash("test_key", nodes)

        assert result is not None
        assert result in nodes

    def test_calculate_node_hash_empty_key_returns_none(self) -> None:
        """Empty affinity key should return None."""
        affinity = ModelSessionAffinity(enabled=True, hash_algorithm="sha256")
        nodes = ["node1", "node2"]

        result = affinity.calculate_node_hash("", nodes)

        assert result is None

    def test_calculate_node_hash_empty_nodes_returns_none(self) -> None:
        """Empty nodes list should return None."""
        affinity = ModelSessionAffinity(enabled=True, hash_algorithm="sha256")

        result = affinity.calculate_node_hash("test_key", [])

        assert result is None

    def test_hash_distribution(self) -> None:
        """Hash should distribute keys across nodes."""
        affinity = ModelSessionAffinity(enabled=True, hash_algorithm="sha256")
        nodes = ["node1", "node2", "node3", "node4", "node5"]

        # Test with multiple keys to check distribution
        results = set()
        for i in range(100):
            result = affinity.calculate_node_hash(f"key_{i}", nodes)
            if result:
                results.add(result)

        # With 100 keys and 5 nodes, we should hit most nodes
        assert len(results) >= 3  # At least 3 different nodes

    def test_different_algorithms_may_produce_different_results(self) -> None:
        """Different algorithms may select different nodes for same key."""
        nodes = ["node1", "node2", "node3", "node4", "node5"]
        test_key = "consistent_test_key"

        affinity_sha256 = ModelSessionAffinity(enabled=True, hash_algorithm="sha256")
        affinity_sha384 = ModelSessionAffinity(enabled=True, hash_algorithm="sha384")
        affinity_sha512 = ModelSessionAffinity(enabled=True, hash_algorithm="sha512")

        result_sha256 = affinity_sha256.calculate_node_hash(test_key, nodes)
        result_sha384 = affinity_sha384.calculate_node_hash(test_key, nodes)
        result_sha512 = affinity_sha512.calculate_node_hash(test_key, nodes)

        # All results should be valid nodes
        assert result_sha256 in nodes
        assert result_sha384 in nodes
        assert result_sha512 in nodes

        # They may or may not differ - just verify they're all valid
        # (We can't guarantee they differ since it depends on hash values)


@pytest.mark.unit
class TestSessionAffinityDefaults:
    """Tests for ModelSessionAffinity default values and configuration."""

    def test_default_enabled_is_false(self) -> None:
        """Session affinity should be disabled by default."""
        affinity = ModelSessionAffinity()
        assert affinity.enabled is False

    def test_default_affinity_type_is_cookie(self) -> None:
        """Default affinity type should be cookie."""
        affinity = ModelSessionAffinity()
        assert affinity.affinity_type == "cookie"

    def test_default_failover_enabled_is_true(self) -> None:
        """Failover should be enabled by default."""
        affinity = ModelSessionAffinity()
        assert affinity.failover_enabled is True

    def test_cookie_secure_defaults_to_true(self) -> None:
        """Cookie secure flag should default to True."""
        affinity = ModelSessionAffinity()
        assert affinity.cookie_secure is True

    def test_cookie_http_only_defaults_to_true(self) -> None:
        """Cookie HTTP-only flag should default to True."""
        affinity = ModelSessionAffinity()
        assert affinity.cookie_http_only is True

    def test_sticky_on_failure_defaults_to_false(self) -> None:
        """Sticky on failure should default to False."""
        affinity = ModelSessionAffinity()
        assert affinity.sticky_on_failure is False

    def test_max_retries_before_failover_default(self) -> None:
        """Max retries before failover should default to 3."""
        affinity = ModelSessionAffinity()
        assert affinity.max_retries_before_failover == 3


@pytest.mark.unit
class TestSessionAffinityGetAffinityKey:
    """Tests for get_affinity_key method."""

    def test_get_affinity_key_disabled_returns_none(self) -> None:
        """When disabled, get_affinity_key should return None."""
        affinity = ModelSessionAffinity(enabled=False)

        result = affinity.get_affinity_key(
            client_ip="192.168.1.1",
            headers={"X-Session": "test"},
            cookies={"session_id": "abc123"},
        )

        assert result is None

    def test_get_affinity_key_ip_hash(self) -> None:
        """IP hash affinity should return client IP."""
        affinity = ModelSessionAffinity(enabled=True, affinity_type="ip_hash")

        result = affinity.get_affinity_key(client_ip="192.168.1.100")

        assert result == "192.168.1.100"

    def test_get_affinity_key_cookie(self) -> None:
        """Cookie affinity should return cookie value."""
        affinity = ModelSessionAffinity(
            enabled=True,
            affinity_type="cookie",
            cookie_name="JSESSIONID",
        )

        result = affinity.get_affinity_key(cookies={"JSESSIONID": "session_value_123"})

        assert result == "session_value_123"

    def test_get_affinity_key_header(self) -> None:
        """Header affinity should return header value."""
        affinity = ModelSessionAffinity(
            enabled=True,
            affinity_type="header",
            header_name="X-Session-ID",
        )

        result = affinity.get_affinity_key(headers={"X-Session-ID": "header_session"})

        assert result == "header_session"

    def test_get_affinity_key_query_param(self) -> None:
        """Query param affinity should return query parameter value."""
        affinity = ModelSessionAffinity(
            enabled=True,
            affinity_type="query_param",
            query_param_name="session",
        )

        result = affinity.get_affinity_key(query_params={"session": "query_session"})

        assert result == "query_session"

    def test_get_affinity_key_missing_cookie_returns_none(self) -> None:
        """Missing cookie should return None."""
        affinity = ModelSessionAffinity(
            enabled=True,
            affinity_type="cookie",
            cookie_name="MISSING",
        )

        result = affinity.get_affinity_key(cookies={"OTHER": "value"})

        assert result is None


@pytest.mark.unit
class TestSessionAffinityBehavior:
    """Tests for session affinity behavior methods."""

    def test_should_create_affinity_when_enabled_and_no_existing(self) -> None:
        """Should create affinity when enabled and no existing affinity."""
        affinity = ModelSessionAffinity(enabled=True)

        assert affinity.should_create_affinity(existing_affinity=None) is True

    def test_should_not_create_affinity_when_disabled(self) -> None:
        """Should not create affinity when disabled."""
        affinity = ModelSessionAffinity(enabled=False)

        assert affinity.should_create_affinity(existing_affinity=None) is False

    def test_should_not_create_affinity_when_existing(self) -> None:
        """Should not create affinity when existing affinity present."""
        affinity = ModelSessionAffinity(enabled=True)

        assert affinity.should_create_affinity(existing_affinity="existing") is False

    def test_should_maintain_affinity_healthy_node(self) -> None:
        """Should maintain affinity when target node is healthy."""
        affinity = ModelSessionAffinity(enabled=True, sticky_on_failure=False)

        assert affinity.should_maintain_affinity(target_node_healthy=True) is True

    def test_should_maintain_affinity_unhealthy_sticky(self) -> None:
        """Should maintain affinity on unhealthy node when sticky_on_failure is True."""
        affinity = ModelSessionAffinity(enabled=True, sticky_on_failure=True)

        assert affinity.should_maintain_affinity(target_node_healthy=False) is True

    def test_should_not_maintain_affinity_unhealthy_not_sticky(self) -> None:
        """Should not maintain affinity on unhealthy node when sticky_on_failure is False."""
        affinity = ModelSessionAffinity(enabled=True, sticky_on_failure=False)

        assert affinity.should_maintain_affinity(target_node_healthy=False) is False

    def test_should_not_maintain_affinity_when_disabled(self) -> None:
        """Should not maintain affinity when disabled."""
        affinity = ModelSessionAffinity(enabled=False)

        assert affinity.should_maintain_affinity(target_node_healthy=True) is False


@pytest.mark.unit
class TestSessionAffinityCookieAttributes:
    """Tests for get_cookie_attributes method."""

    def test_cookie_attributes_disabled(self) -> None:
        """Should return empty dict when disabled."""
        affinity = ModelSessionAffinity(enabled=False)

        assert affinity.get_cookie_attributes() == {}

    def test_cookie_attributes_non_cookie_type(self) -> None:
        """Should return empty dict for non-cookie affinity types."""
        affinity = ModelSessionAffinity(enabled=True, affinity_type="ip_hash")

        assert affinity.get_cookie_attributes() == {}

    def test_cookie_attributes_basic(self) -> None:
        """Should return basic secure and httponly attributes."""
        affinity = ModelSessionAffinity(
            enabled=True,
            affinity_type="cookie",
            cookie_secure=True,
            cookie_http_only=True,
        )

        attrs = affinity.get_cookie_attributes()

        assert attrs["secure"] is True
        assert attrs["httponly"] is True

    def test_cookie_attributes_with_optional_fields(self) -> None:
        """Should include optional fields when set."""
        affinity = ModelSessionAffinity(
            enabled=True,
            affinity_type="cookie",
            cookie_ttl_seconds=3600,
            cookie_domain=".example.com",
            cookie_path="/app",
        )

        attrs = affinity.get_cookie_attributes()

        assert attrs["max_age"] == 3600
        assert attrs["domain"] == ".example.com"
        assert attrs["path"] == "/app"


@pytest.mark.unit
class TestSessionAffinityValidation:
    """Tests for field validation constraints."""

    def test_cookie_ttl_minimum(self) -> None:
        """Cookie TTL must be at least 60 seconds."""
        with pytest.raises(ValidationError):
            ModelSessionAffinity(cookie_ttl_seconds=59)

        # 60 should be valid
        affinity = ModelSessionAffinity(cookie_ttl_seconds=60)
        assert affinity.cookie_ttl_seconds == 60

    def test_cookie_ttl_maximum(self) -> None:
        """Cookie TTL must not exceed 24 hours (86400 seconds)."""
        with pytest.raises(ValidationError):
            ModelSessionAffinity(cookie_ttl_seconds=86401)

        # 86400 should be valid
        affinity = ModelSessionAffinity(cookie_ttl_seconds=86400)
        assert affinity.cookie_ttl_seconds == 86400

    def test_session_timeout_minimum(self) -> None:
        """Session timeout must be at least 5 minutes (300 seconds)."""
        with pytest.raises(ValidationError):
            ModelSessionAffinity(session_timeout_seconds=299)

        # 300 should be valid
        affinity = ModelSessionAffinity(session_timeout_seconds=300)
        assert affinity.session_timeout_seconds == 300

    def test_session_timeout_maximum(self) -> None:
        """Session timeout must not exceed 24 hours (86400 seconds)."""
        with pytest.raises(ValidationError):
            ModelSessionAffinity(session_timeout_seconds=86401)

        # 86400 should be valid
        affinity = ModelSessionAffinity(session_timeout_seconds=86400)
        assert affinity.session_timeout_seconds == 86400

    def test_max_retries_minimum(self) -> None:
        """Max retries must be at least 1."""
        with pytest.raises(ValidationError):
            ModelSessionAffinity(max_retries_before_failover=0)

        # 1 should be valid
        affinity = ModelSessionAffinity(max_retries_before_failover=1)
        assert affinity.max_retries_before_failover == 1

    def test_max_retries_maximum(self) -> None:
        """Max retries must not exceed 10."""
        with pytest.raises(ValidationError):
            ModelSessionAffinity(max_retries_before_failover=11)

        # 10 should be valid
        affinity = ModelSessionAffinity(max_retries_before_failover=10)
        assert affinity.max_retries_before_failover == 10

    def test_affinity_type_validation(self) -> None:
        """Only valid affinity types should be accepted."""
        valid_types = ["cookie", "ip_hash", "header", "query_param", "custom"]

        for valid_type in valid_types:
            affinity = ModelSessionAffinity(affinity_type=valid_type)
            assert affinity.affinity_type == valid_type

        with pytest.raises(ValidationError):
            ModelSessionAffinity(affinity_type="invalid_type")
