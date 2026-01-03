"""
ModelPerUserLimits - Per-user rate limiting configuration

Per-user limits model for defining user-specific rate limiting rules
with user tiers, quotas, and individual user overrides.
"""

from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.types import SerializedDict


class ModelPerUserLimits(BaseModel):
    """
    Per-user rate limiting configuration

    This model defines how rate limits should be applied on a per-user basis,
    including user tiers, quotas, individual overrides, and user identification.
    """

    enabled: bool = Field(
        default=True, description="Whether per-user rate limiting is enabled"
    )
    default_user_limit: int = Field(
        default=100,
        description="Default rate limit for unspecified users",
        ge=1,
        le=1000000,
    )
    user_identification_method: str = Field(
        default="user_id",
        description="Method to identify users",
        pattern="^(user_id|api_key|ip_address|session_id|custom_header|jwt_subject)$",
    )
    user_identification_header: str | None = Field(
        default=None,
        description="Header name for user identification (if using custom_header)",
    )
    anonymous_user_limit: int = Field(
        default=20,
        description="Rate limit for anonymous/unidentified users",
        ge=1,
        le=100000,
    )
    user_tier_limits: dict[str, int] = Field(
        default_factory=lambda: {"free": 100, "premium": 1000, "enterprise": 10000},
        description="Rate limits by user tier",
    )
    individual_user_overrides: dict[UUID, int] = Field(
        default_factory=dict, description="Specific rate limits for individual users"
    )
    blocked_users: list[UUID] = Field(
        default_factory=list, description="Users that are completely blocked"
    )
    unlimited_users: list[UUID] = Field(
        default_factory=list, description="Users with unlimited access"
    )
    user_quota_enabled: bool = Field(
        default=False,
        description="Whether user quotas (daily/monthly limits) are enabled",
    )
    daily_quota_limits: dict[str, int] = Field(
        default_factory=dict, description="Daily quota limits by user tier"
    )
    monthly_quota_limits: dict[str, int] = Field(
        default_factory=dict, description="Monthly quota limits by user tier"
    )
    quota_reset_hour: int = Field(
        default=0, description="Hour of day (0-23) when daily quotas reset", ge=0, le=23
    )
    grace_period_minutes: int = Field(
        default=5,
        description="Grace period for new users before rate limiting applies",
        ge=0,
        le=60,
    )
    burst_allowance_per_user: float | None = Field(
        default=None,
        description="Additional burst capacity multiplier per user",
        ge=1.0,
        le=5.0,
    )
    user_specific_burst: dict[UUID, float] = Field(
        default_factory=dict, description="User-specific burst multipliers"
    )
    escalation_enabled: bool = Field(
        default=True, description="Whether to escalate limits for trusted users"
    )
    escalation_trust_threshold: float = Field(
        default=0.8,
        description="Trust score threshold for automatic escalation",
        ge=0.0,
        le=1.0,
    )
    escalation_multiplier: float = Field(
        default=1.5, description="Multiplier for escalated user limits", ge=1.0, le=5.0
    )

    def get_user_limit(self, user_id: UUID, user_tier: str | None = None) -> int:
        """Get rate limit for a specific user"""
        if not self.enabled:
            return self.default_user_limit
        if user_id in self.blocked_users:
            return 0
        if user_id in self.unlimited_users:
            return 1000000
        if user_id in self.individual_user_overrides:
            return self.individual_user_overrides[user_id]
        if user_tier and user_tier in self.user_tier_limits:
            return self.user_tier_limits[user_tier]
        return self.default_user_limit

    def get_user_burst_capacity(self, user_id: UUID, base_limit: int) -> int:
        """Get burst capacity for a specific user"""
        if user_id in self.user_specific_burst:
            multiplier = self.user_specific_burst[user_id]
        elif self.burst_allowance_per_user:
            multiplier = self.burst_allowance_per_user
        else:
            return base_limit
        return int(base_limit * multiplier)

    def get_daily_quota(self, user_tier: str | None = None) -> int | None:
        """Get daily quota for a user tier"""
        if not self.user_quota_enabled or not user_tier:
            return None
        return self.daily_quota_limits.get(user_tier)

    def get_monthly_quota(self, user_tier: str | None = None) -> int | None:
        """Get monthly quota for a user tier"""
        if not self.user_quota_enabled or not user_tier:
            return None
        return self.monthly_quota_limits.get(user_tier)

    def is_user_blocked(self, user_id: UUID) -> bool:
        """Check if user is completely blocked"""
        return user_id in self.blocked_users

    def is_user_unlimited(self, user_id: UUID) -> bool:
        """Check if user has unlimited access"""
        return user_id in self.unlimited_users

    def should_escalate_user(self, user_id: UUID, trust_score: float) -> bool:
        """Check if user should get escalated limits based on trust"""
        if not self.escalation_enabled:
            return False
        return trust_score >= self.escalation_trust_threshold

    def get_escalated_limit(self, base_limit: int) -> int:
        """Calculate escalated limit for trusted users"""
        return int(base_limit * self.escalation_multiplier)

    def extract_user_id(
        self,
        headers: dict[str, str],
        query_params: dict[str, str] | None = None,
        client_ip: str = "",
        jwt_payload: SerializedDict | None = None,
    ) -> str | None:
        """Extract user ID based on identification method"""
        query_params = query_params or {}
        jwt_payload = jwt_payload or {}
        if self.user_identification_method == "user_id":
            return headers.get("X-User-ID") or query_params.get("user_id")
        if self.user_identification_method == "api_key":
            return headers.get("X-API-Key") or headers.get("Authorization", "").replace(
                "Bearer ", ""
            )
        if self.user_identification_method == "ip_address":
            return client_ip
        if self.user_identification_method == "session_id":
            return headers.get("X-Session-ID") or query_params.get("session_id")
        if (
            self.user_identification_method == "custom_header"
            and self.user_identification_header
        ):
            return headers.get(self.user_identification_header)
        if self.user_identification_method == "jwt_subject":
            sub = jwt_payload.get("sub")
            return str(sub) if isinstance(sub, str) else None
        return None

    def add_user_override(self, user_id: UUID, limit: int) -> None:
        """Add individual user override"""
        self.individual_user_overrides[user_id] = limit

    def remove_user_override(self, user_id: UUID) -> None:
        """Remove individual user override"""
        self.individual_user_overrides.pop(user_id, None)

    def block_user(self, user_id: UUID) -> None:
        """Block a user completely"""
        if user_id not in self.blocked_users:
            self.blocked_users.append(user_id)
        if user_id in self.unlimited_users:
            self.unlimited_users.remove(user_id)

    def unblock_user(self, user_id: UUID) -> None:
        """Unblock a previously blocked user"""
        if user_id in self.blocked_users:
            self.blocked_users.remove(user_id)

    def grant_unlimited_access(self, user_id: UUID) -> None:
        """Grant unlimited access to a user"""
        if user_id not in self.unlimited_users:
            self.unlimited_users.append(user_id)
        if user_id in self.blocked_users:
            self.blocked_users.remove(user_id)

    def revoke_unlimited_access(self, user_id: UUID) -> None:
        """Revoke unlimited access from a user"""
        if user_id in self.unlimited_users:
            self.unlimited_users.remove(user_id)

    @classmethod
    def create_basic_user_limits(cls) -> "ModelPerUserLimits":
        """Create basic per-user rate limiting configuration"""
        return cls(
            enabled=True,
            default_user_limit=100,
            anonymous_user_limit=20,
            user_identification_method="api_key",
            user_tier_limits={"free": 50, "paid": 500, "premium": 2000},
        )

    @classmethod
    def create_enterprise_user_limits(cls) -> "ModelPerUserLimits":
        """Create enterprise per-user rate limiting with quotas"""
        return cls(
            enabled=True,
            default_user_limit=1000,
            anonymous_user_limit=10,
            user_identification_method="jwt_subject",
            user_tier_limits={"basic": 1000, "professional": 5000, "enterprise": 20000},
            user_quota_enabled=True,
            daily_quota_limits={
                "basic": 50000,
                "professional": 200000,
                "enterprise": 1000000,
            },
            escalation_enabled=True,
            burst_allowance_per_user=2.0,
        )

    @classmethod
    def create_api_key_limits(cls) -> "ModelPerUserLimits":
        """Create API key-based rate limiting configuration"""
        return cls(
            enabled=True,
            default_user_limit=200,
            anonymous_user_limit=5,
            user_identification_method="api_key",
            user_tier_limits={
                "trial": 100,
                "standard": 1000,
                "pro": 5000,
                "enterprise": 25000,
            },
            grace_period_minutes=10,
            escalation_enabled=True,
        )

    @classmethod
    def create_ip_based_limits(cls) -> "ModelPerUserLimits":
        """Create IP-based rate limiting configuration"""
        return cls(
            enabled=True,
            default_user_limit=100,
            anonymous_user_limit=100,
            user_identification_method="ip_address",
            escalation_enabled=False,
            burst_allowance_per_user=1.5,
        )
