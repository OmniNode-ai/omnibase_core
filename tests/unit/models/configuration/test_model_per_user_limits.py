"""Tests for ModelPerUserLimits - Per-user rate limiting configuration."""

from uuid import uuid4

import pytest

from omnibase_core.models.configuration.model_per_user_limits import ModelPerUserLimits


@pytest.mark.unit
class TestModelPerUserLimitsBasics:
    """Test basic initialization and validation."""

    def test_create_default(self):
        limits = ModelPerUserLimits()
        assert limits.enabled is True
        assert limits.default_user_limit == 100
        assert limits.user_identification_method == "user_id"

    def test_create_with_custom_values(self):
        limits = ModelPerUserLimits(
            default_user_limit=500,
            anonymous_user_limit=50,
            user_identification_method="api_key",
        )
        assert limits.default_user_limit == 500
        assert limits.anonymous_user_limit == 50
        assert limits.user_identification_method == "api_key"

    def test_user_tier_limits_default(self):
        limits = ModelPerUserLimits()
        assert "free" in limits.user_tier_limits
        assert "premium" in limits.user_tier_limits
        assert limits.user_tier_limits["free"] == 100


@pytest.mark.unit
class TestModelPerUserLimitsUserManagement:
    """Test user limit management methods."""

    def test_get_user_limit_default(self):
        limits = ModelPerUserLimits(default_user_limit=100)
        user_id = uuid4()
        limit = limits.get_user_limit(user_id)
        assert limit == 100

    def test_get_user_limit_blocked(self):
        limits = ModelPerUserLimits()
        user_id = uuid4()
        limits.block_user(user_id)
        limit = limits.get_user_limit(user_id)
        assert limit == 0

    def test_get_user_limit_unlimited(self):
        limits = ModelPerUserLimits()
        user_id = uuid4()
        limits.grant_unlimited_access(user_id)
        limit = limits.get_user_limit(user_id)
        assert limit == 1000000

    def test_get_user_limit_override(self):
        limits = ModelPerUserLimits()
        user_id = uuid4()
        limits.add_user_override(user_id, 5000)
        limit = limits.get_user_limit(user_id)
        assert limit == 5000

    def test_get_user_limit_by_tier(self):
        limits = ModelPerUserLimits(user_tier_limits={"basic": 100, "pro": 1000})
        user_id = uuid4()
        limit = limits.get_user_limit(user_id, "pro")
        assert limit == 1000


@pytest.mark.unit
class TestModelPerUserLimitsBurst:
    """Test burst capacity methods."""

    def test_get_user_burst_capacity_default(self):
        limits = ModelPerUserLimits()
        user_id = uuid4()
        burst = limits.get_user_burst_capacity(user_id, 100)
        assert burst == 100  # No multiplier, returns base

    def test_get_user_burst_capacity_with_default_multiplier(self):
        limits = ModelPerUserLimits(burst_allowance_per_user=2.0)
        user_id = uuid4()
        burst = limits.get_user_burst_capacity(user_id, 100)
        assert burst == 200

    def test_get_user_burst_capacity_user_specific(self):
        limits = ModelPerUserLimits()
        user_id = uuid4()
        limits.user_specific_burst[user_id] = 3.0
        burst = limits.get_user_burst_capacity(user_id, 100)
        assert burst == 300


@pytest.mark.unit
class TestModelPerUserLimitsQuotas:
    """Test quota management methods."""

    def test_get_daily_quota_disabled(self):
        limits = ModelPerUserLimits(user_quota_enabled=False)
        quota = limits.get_daily_quota("premium")
        assert quota is None

    def test_get_daily_quota_enabled(self):
        limits = ModelPerUserLimits(
            user_quota_enabled=True, daily_quota_limits={"premium": 100000}
        )
        quota = limits.get_daily_quota("premium")
        assert quota == 100000

    def test_get_monthly_quota_enabled(self):
        limits = ModelPerUserLimits(
            user_quota_enabled=True, monthly_quota_limits={"premium": 3000000}
        )
        quota = limits.get_monthly_quota("premium")
        assert quota == 3000000


@pytest.mark.unit
class TestModelPerUserLimitsUserChecks:
    """Test user status check methods."""

    def test_is_user_blocked(self):
        limits = ModelPerUserLimits()
        user_id = uuid4()
        assert limits.is_user_blocked(user_id) is False
        limits.block_user(user_id)
        assert limits.is_user_blocked(user_id) is True

    def test_is_user_unlimited(self):
        limits = ModelPerUserLimits()
        user_id = uuid4()
        assert limits.is_user_unlimited(user_id) is False
        limits.grant_unlimited_access(user_id)
        assert limits.is_user_unlimited(user_id) is True

    def test_block_removes_unlimited(self):
        limits = ModelPerUserLimits()
        user_id = uuid4()
        limits.grant_unlimited_access(user_id)
        limits.block_user(user_id)
        assert limits.is_user_unlimited(user_id) is False
        assert limits.is_user_blocked(user_id) is True


@pytest.mark.unit
class TestModelPerUserLimitsEscalation:
    """Test escalation methods."""

    def test_should_escalate_user_enabled(self):
        limits = ModelPerUserLimits(
            escalation_enabled=True, escalation_trust_threshold=0.8
        )
        user_id = uuid4()
        assert limits.should_escalate_user(user_id, 0.9) is True
        assert limits.should_escalate_user(user_id, 0.7) is False

    def test_should_escalate_user_disabled(self):
        limits = ModelPerUserLimits(escalation_enabled=False)
        user_id = uuid4()
        assert limits.should_escalate_user(user_id, 1.0) is False

    def test_get_escalated_limit(self):
        limits = ModelPerUserLimits(escalation_multiplier=2.0)
        escalated = limits.get_escalated_limit(100)
        assert escalated == 200


@pytest.mark.unit
class TestModelPerUserLimitsUserIdentification:
    """Test user identification extraction."""

    def test_extract_user_id_from_header(self):
        limits = ModelPerUserLimits(user_identification_method="user_id")
        user_id = limits.extract_user_id(
            headers={"X-User-ID": "user123"}, query_params={}, client_ip=""
        )
        assert user_id == "user123"

    def test_extract_api_key(self):
        limits = ModelPerUserLimits(user_identification_method="api_key")
        user_id = limits.extract_user_id(
            headers={"X-API-Key": "key123"}, query_params={}, client_ip=""
        )
        assert user_id == "key123"

    def test_extract_ip_address(self):
        limits = ModelPerUserLimits(user_identification_method="ip_address")
        user_id = limits.extract_user_id(
            headers={}, query_params={}, client_ip="192.168.1.1"
        )
        assert user_id == "192.168.1.1"

    def test_extract_custom_header(self):
        limits = ModelPerUserLimits(
            user_identification_method="custom_header",
            user_identification_header="X-Custom-ID",
        )
        user_id = limits.extract_user_id(
            headers={"X-Custom-ID": "custom123"}, query_params={}, client_ip=""
        )
        assert user_id == "custom123"


@pytest.mark.unit
class TestModelPerUserLimitsFactoryMethods:
    """Test factory methods."""

    def test_create_basic_user_limits(self):
        limits = ModelPerUserLimits.create_basic_user_limits()
        assert limits.enabled is True
        assert limits.default_user_limit == 100
        assert limits.user_identification_method == "api_key"

    def test_create_enterprise_user_limits(self):
        limits = ModelPerUserLimits.create_enterprise_user_limits()
        assert limits.user_quota_enabled is True
        assert limits.escalation_enabled is True
        assert limits.burst_allowance_per_user == 2.0

    def test_create_api_key_limits(self):
        limits = ModelPerUserLimits.create_api_key_limits()
        assert limits.user_identification_method == "api_key"
        assert limits.grace_period_minutes == 10

    def test_create_ip_based_limits(self):
        limits = ModelPerUserLimits.create_ip_based_limits()
        assert limits.user_identification_method == "ip_address"
        assert limits.escalation_enabled is False


@pytest.mark.unit
class TestModelPerUserLimitsManagement:
    """Test user management operations."""

    def test_add_remove_user_override(self):
        limits = ModelPerUserLimits()
        user_id = uuid4()
        limits.add_user_override(user_id, 5000)
        assert limits.individual_user_overrides[user_id] == 5000
        limits.remove_user_override(user_id)
        assert user_id not in limits.individual_user_overrides

    def test_block_unblock_user(self):
        limits = ModelPerUserLimits()
        user_id = uuid4()
        limits.block_user(user_id)
        assert user_id in limits.blocked_users
        limits.unblock_user(user_id)
        assert user_id not in limits.blocked_users

    def test_grant_revoke_unlimited(self):
        limits = ModelPerUserLimits()
        user_id = uuid4()
        limits.grant_unlimited_access(user_id)
        assert user_id in limits.unlimited_users
        limits.revoke_unlimited_access(user_id)
        assert user_id not in limits.unlimited_users


@pytest.mark.unit
class TestModelPerUserLimitsSerialization:
    """Test serialization."""

    def test_serialization(self):
        limits = ModelPerUserLimits(default_user_limit=500)
        data = limits.model_dump()
        assert data["default_user_limit"] == 500

    def test_deserialization(self):
        data = {"default_user_limit": 500}
        limits = ModelPerUserLimits.model_validate(data)
        assert limits.default_user_limit == 500

    def test_roundtrip(self):
        original = ModelPerUserLimits(default_user_limit=500)
        data = original.model_dump()
        restored = ModelPerUserLimits.model_validate(data)
        assert restored.default_user_limit == original.default_user_limit
