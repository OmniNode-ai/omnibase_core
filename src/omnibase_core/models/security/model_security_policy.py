"""
Security policy model with structured data fields.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from .model_security_context import ModelSecurityContext
from .model_security_policy_data import ModelSecurityPolicyData
from .model_security_rule import ModelSecurityRule
from .model_time_restrictions import ModelTimeRestrictions

# Compatibility aliases
SecurityRule = ModelSecurityRule
SecurityContext = ModelSecurityContext


class ModelSecurityPolicy(BaseModel):
    """
    Security policy model with structured typed fields for comprehensive policy management.
    """

    # Policy identification
    policy_id: str = Field(..., description="Unique policy identifier")
    policy_name: str = Field(..., description="Human-readable policy name")
    policy_version: str = Field("1.0.0", description="Policy version")

    # Policy metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation time",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update time",
    )
    created_by: str | None = Field(None, description="Policy creator")
    description: str | None = Field(None, description="Policy description")

    # Access control
    access_control_model: str = Field(
        "RBAC",
        description="Access control model (RBAC/ABAC/etc)",
    )
    default_action: str = Field("deny", description="Default action (allow/deny)")

    # Security rules
    rules: list[ModelSecurityRule] = Field(
        default_factory=list,
        description="Security rules",
    )

    # Authentication requirements
    require_authentication: bool = Field(True, description="Require authentication")
    allowed_auth_methods: list[str] = Field(
        default_factory=list,
        description="Allowed authentication methods",
    )
    require_mfa: bool = Field(False, description="Require multi-factor authentication")

    # Session management
    session_timeout_minutes: int | None = Field(30, description="Session timeout")
    max_sessions_per_user: int | None = Field(
        5,
        description="Max concurrent sessions",
    )

    # IP restrictions
    allowed_ip_ranges: list[str] = Field(
        default_factory=list,
        description="Allowed IP ranges (CIDR notation)",
    )
    denied_ip_ranges: list[str] = Field(
        default_factory=list,
        description="Denied IP ranges (CIDR notation)",
    )

    # Time-based restrictions
    valid_from: datetime | None = Field(None, description="Policy valid from")
    valid_until: datetime | None = Field(None, description="Policy valid until")
    time_restrictions: ModelTimeRestrictions | None = Field(
        None,
        description="Time-based access restrictions",
    )

    # Compliance tags
    compliance_frameworks: list[str] = Field(
        default_factory=list,
        description="Compliance frameworks (SOC2, HIPAA, etc)",
    )
    data_classification: str | None = Field(
        None,
        description="Data classification level",
    )

    model_config = ConfigDict()

    def to_dict(self) -> ModelSecurityPolicyData:
        """Convert to data container for current standards."""
        # Custom transformation using model_dump() in data container
        return ModelSecurityPolicyData(typed_data=self.model_dump(exclude_none=True))

    @classmethod
    def from_dict(cls, data: ModelSecurityPolicyData) -> "ModelSecurityPolicy":
        """Create from data container for easy migration."""
        return cls(**data.typed_data)

    @field_serializer("created_at", "updated_at", "valid_from", "valid_until")
    def serialize_datetime(self, value):
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
