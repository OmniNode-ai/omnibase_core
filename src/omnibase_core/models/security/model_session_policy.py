"""
Session Policy Model

Typed model for session management policy configuration,
replacing Dict[str, Any] with structured fields.
"""

from pydantic import BaseModel, Field


class ModelSessionPolicy(BaseModel):
    """
    Structured session management policy configuration.

    Defines session lifecycle, timeout, and security constraints.
    """

    # Session duration
    max_duration_minutes: int = Field(
        default=480,  # 8 hours
        description="Maximum session duration in minutes",
        ge=1,
        le=10080,  # 1 week max
    )

    idle_timeout_minutes: int = Field(
        default=30,
        description="Session idle timeout in minutes",
        ge=1,
        le=1440,  # 24 hours max
    )

    absolute_timeout_minutes: int | None = Field(
        default=None,
        description="Absolute session timeout regardless of activity",
        ge=1,
    )

    # Session limits
    concurrent_sessions: int = Field(
        default=3,
        description="Maximum concurrent sessions per user",
        ge=1,
        le=100,
    )

    max_sessions_per_ip: int | None = Field(
        default=10,
        description="Maximum sessions from same IP address",
        ge=1,
    )

    max_sessions_per_device: int | None = Field(
        default=1,
        description="Maximum sessions per device",
        ge=1,
    )

    # Authentication requirements
    require_fresh_auth_for_sensitive: bool = Field(
        default=True,
        description="Require fresh authentication for sensitive operations",
    )

    fresh_auth_timeout_minutes: int = Field(
        default=5,
        description="How long authentication is considered 'fresh'",
        ge=1,
    )

    require_mfa_for_session: bool = Field(
        default=False,
        description="Require multi-factor authentication for session creation",
    )

    # Session persistence
    persist_sessions: bool = Field(
        default=True,
        description="Whether to persist sessions across server restarts",
    )

    session_cookie_secure: bool = Field(
        default=True,
        description="Set secure flag on session cookies (HTTPS only)",
    )

    session_cookie_httponly: bool = Field(
        default=True,
        description="Set HttpOnly flag on session cookies",
    )

    session_cookie_samesite: str = Field(
        default="Strict",
        description="SameSite attribute for session cookies",
        pattern="^(Strict|Lax|None)$",
    )

    # IP and location restrictions
    bind_session_to_ip: bool = Field(
        default=False,
        description="Bind session to originating IP address",
    )

    allowed_ip_ranges: list[str] = Field(
        default_factory=list,
        description="Allowed IP ranges for sessions (CIDR notation)",
    )

    geo_restrictions_enabled: bool = Field(
        default=False,
        description="Enable geographic restrictions on sessions",
    )

    allowed_countries: list[str] = Field(
        default_factory=list,
        description="Allowed countries for sessions (ISO codes)",
    )

    blocked_countries: list[str] = Field(
        default_factory=list,
        description="Blocked countries for sessions (ISO codes)",
    )

    # Session behavior
    extend_on_activity: bool = Field(
        default=True,
        description="Extend session timeout on user activity",
    )

    warn_before_timeout_minutes: int = Field(
        default=5,
        description="Warn user before session timeout",
        ge=0,
    )

    allow_remember_me: bool = Field(
        default=True,
        description="Allow 'remember me' functionality",
    )

    remember_me_duration_days: int = Field(
        default=30,
        description="Duration for 'remember me' sessions in days",
        ge=1,
        le=365,
    )

    # Logout behavior
    logout_on_browser_close: bool = Field(
        default=False,
        description="Force logout when browser is closed",
    )

    invalidate_all_on_password_change: bool = Field(
        default=True,
        description="Invalidate all sessions on password change",
    )

    invalidate_all_on_privilege_change: bool = Field(
        default=True,
        description="Invalidate all sessions on privilege change",
    )

    # Session monitoring
    track_session_activity: bool = Field(
        default=True,
        description="Track detailed session activity",
    )

    store_session_metadata: bool = Field(
        default=True,
        description="Store session metadata (user agent, IP, etc.)",
    )

    alert_on_suspicious_activity: bool = Field(
        default=True,
        description="Alert on suspicious session activity",
    )

    @classmethod
    def create_minimal(cls) -> "ModelSessionPolicy":
        """Create minimal session policy."""
        return cls(
            max_duration_minutes=1440,  # 24 hours
            idle_timeout_minutes=120,  # 2 hours
            concurrent_sessions=10,
            require_fresh_auth_for_sensitive=False,
            session_cookie_secure=False,
            bind_session_to_ip=False,
            track_session_activity=False,
        )

    @classmethod
    def create_standard(cls) -> "ModelSessionPolicy":
        """Create standard session policy."""
        return cls()  # Use defaults

    @classmethod
    def create_strict(cls) -> "ModelSessionPolicy":
        """Create strict session policy."""
        return cls(
            max_duration_minutes=240,  # 4 hours
            idle_timeout_minutes=15,
            concurrent_sessions=1,
            require_fresh_auth_for_sensitive=True,
            fresh_auth_timeout_minutes=3,
            require_mfa_for_session=True,
            bind_session_to_ip=True,
            extend_on_activity=False,
            logout_on_browser_close=True,
        )

    @classmethod
    def create_maximum(cls) -> "ModelSessionPolicy":
        """Create maximum security session policy."""
        return cls(
            max_duration_minutes=120,  # 2 hours
            idle_timeout_minutes=10,
            absolute_timeout_minutes=120,
            concurrent_sessions=1,
            max_sessions_per_ip=1,
            max_sessions_per_device=1,
            require_fresh_auth_for_sensitive=True,
            fresh_auth_timeout_minutes=1,
            require_mfa_for_session=True,
            session_cookie_secure=True,
            session_cookie_httponly=True,
            session_cookie_samesite="Strict",
            bind_session_to_ip=True,
            geo_restrictions_enabled=True,
            extend_on_activity=False,
            warn_before_timeout_minutes=2,
            allow_remember_me=False,
            logout_on_browser_close=True,
            track_session_activity=True,
            alert_on_suspicious_activity=True,
        )
