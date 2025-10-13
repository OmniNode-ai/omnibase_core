"""Tests for ModelRateLimitPolicy."""

from uuid import uuid4

import pytest

from omnibase_core.models.configuration.model_rate_limit_policy import (
    ModelRateLimitPolicy,
)


class TestModelRateLimitPolicyBasics:
    def test_create_with_required_fields(self):
        policy = ModelRateLimitPolicy(policy_name="test-policy")
        assert policy.policy_name == "test-policy"
        assert policy.enabled is True

    def test_policy_name_validation(self):
        policy = ModelRateLimitPolicy(policy_name="test-policy")
        assert policy.policy_name == "test-policy"
        with pytest.raises(ValueError):
            ModelRateLimitPolicy(policy_name="Invalid Policy")


class TestModelRateLimitPolicyMethods:
    def test_get_effective_rate_limit_disabled(self):
        policy = ModelRateLimitPolicy(policy_name="test", enabled=False)
        limit = policy.get_effective_rate_limit()
        assert limit == float("inf")

    def test_get_effective_rate_limit_global(self):
        policy = ModelRateLimitPolicy(policy_name="test", global_rate_limit=100.0)
        limit = policy.get_effective_rate_limit()
        # Returns minimum of all applicable limits including window config
        assert limit <= 100.0

    def test_get_effective_rate_limit_endpoint(self):
        policy = ModelRateLimitPolicy(
            policy_name="test", per_endpoint_limits={"/api/users": 50.0}
        )
        limit = policy.get_effective_rate_limit(endpoint="/api/users")
        # Returns minimum of all applicable limits
        assert limit <= 50.0

    def test_is_ip_whitelisted(self):
        policy = ModelRateLimitPolicy(policy_name="test", ip_whitelist=["192.168.1.1"])
        assert policy.is_ip_whitelisted("192.168.1.1") is True
        assert policy.is_ip_whitelisted("10.0.0.1") is False

    def test_is_ip_blacklisted(self):
        policy = ModelRateLimitPolicy(policy_name="test", ip_blacklist=["10.0.0.1"])
        assert policy.is_ip_blacklisted("10.0.0.1") is True
        assert policy.is_ip_blacklisted("192.168.1.1") is False

    def test_get_cache_key(self):
        policy = ModelRateLimitPolicy(policy_name="test-policy", cache_key_prefix="rl")
        key = policy.get_cache_key("user123", "user")
        assert key == "rl:test-policy:user:user123"

    def test_calculate_retry_after(self):
        policy = ModelRateLimitPolicy(policy_name="test")
        retry_after = policy.calculate_retry_after(0.0)
        assert retry_after >= 1
        assert retry_after <= 3600

    def test_get_monitoring_metrics(self):
        policy = ModelRateLimitPolicy(policy_name="test")
        metrics = policy.get_monitoring_metrics()
        assert isinstance(metrics, dict)
        assert "requests_per_second" in metrics

    def test_validate_policy_consistency(self):
        policy = ModelRateLimitPolicy(policy_name="test")
        issues = policy.validate_policy_consistency()
        assert isinstance(issues, list)


class TestModelRateLimitPolicySerialization:
    def test_serialization(self):
        policy = ModelRateLimitPolicy(policy_name="test")
        data = policy.model_dump()
        assert data["policy_name"] == "test"

    def test_roundtrip(self):
        original = ModelRateLimitPolicy(policy_name="test")
        data = original.model_dump()
        restored = ModelRateLimitPolicy.model_validate(data)
        assert restored.policy_name == original.policy_name
