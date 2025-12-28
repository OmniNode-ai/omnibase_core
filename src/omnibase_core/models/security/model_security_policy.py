"""Security policy model with structured data fields.

Provides comprehensive security policy management with typed fields for
access control, authentication requirements, IP restrictions, and compliance.
"""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from omnibase_core.models.common.model_typed_mapping import ModelTypedMapping
from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_security_context import ModelSecurityContext
from .model_security_policy_data import ModelSecurityPolicyData
from .model_security_rule import ModelSecurityRule
from .model_time_restrictions import ModelTimeRestrictions

SecurityRule = ModelSecurityRule
SecurityContext = ModelSecurityContext


class ModelSecurityPolicy(BaseModel):
    """Security policy model with structured typed fields for comprehensive policy management.

    Defines access control rules, authentication requirements, IP restrictions,
    time-based access controls, and compliance framework associations.

    Note:
        This model uses from_attributes=True to support pytest-xdist parallel
        execution where class identity may differ between workers.
    """

    policy_id: UUID = Field(default=..., description="Unique policy identifier")
    policy_name: str = Field(default=..., description="Human-readable policy name")
    policy_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Policy version",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Creation time"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last update time"
    )
    created_by: str | None = Field(default=None, description="Policy creator")
    description: str | None = Field(default=None, description="Policy description")
    access_control_model: str = Field(
        default="RBAC", description="Access control model (RBAC/ABAC/etc)"
    )
    default_action: str = Field(
        default="deny", description="Default action (allow/deny)"
    )
    rules: list[ModelSecurityRule] = Field(
        default_factory=list, description="Security rules"
    )
    require_authentication: bool = Field(
        default=True, description="Require authentication"
    )
    allowed_auth_methods: list[str] = Field(
        default_factory=list, description="Allowed authentication methods"
    )
    require_mfa: bool = Field(
        default=False, description="Require multi-factor authentication"
    )
    session_timeout_minutes: int | None = Field(
        default=30, description="Session timeout"
    )
    max_sessions_per_user: int | None = Field(
        default=5, description="Max concurrent sessions"
    )
    allowed_ip_ranges: list[str] = Field(
        default_factory=list, description="Allowed IP ranges (CIDR notation)"
    )
    denied_ip_ranges: list[str] = Field(
        default_factory=list, description="Denied IP ranges (CIDR notation)"
    )
    valid_from: datetime | None = Field(default=None, description="Policy valid from")
    valid_until: datetime | None = Field(default=None, description="Policy valid until")
    time_restrictions: ModelTimeRestrictions | None = Field(
        default=None, description="Time-based access restrictions"
    )
    compliance_frameworks: list[str] = Field(
        default_factory=list, description="Compliance frameworks (SOC2, HIPAA, etc)"
    )
    data_classification: str | None = Field(
        default=None, description="Data classification level"
    )

    model_config = ConfigDict(from_attributes=True)

    def to_dict(self) -> ModelSecurityPolicyData:
        """Convert to data container for current standards."""
        typed_mapping = ModelTypedMapping()
        for key, value in self.model_dump(exclude_none=True).items():
            typed_mapping.set_value(key, value)
        return ModelSecurityPolicyData(typed_data=typed_mapping)

    @classmethod
    def from_dict(cls, data: ModelSecurityPolicyData) -> "ModelSecurityPolicy":
        """Create from data container for easy migration."""
        data_dict = data.typed_data.to_python_dict()
        return cls(**data_dict)  # type: ignore[arg-type]

    @field_serializer("created_at", "updated_at", "valid_from", "valid_until")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value:
            return value.isoformat()
        return None
