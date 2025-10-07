from typing import Any, Dict

from pydantic import Field

"""
Security policy model with structured data fields.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from omnibase_core.models.core.model_semver import ModelSemVer

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
    policy_id: str = Field(default=..., description="Unique policy identifier")
    policy_name: str = Field(default=..., description="Human-readable policy name")
    policy_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Policy version",
    )

    # Policy metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation time",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update time",
    )
    created_by: str | None = Field(default=None, description="Policy creator")
    description: str | None = Field(default=None, description="Policy description")

    # Access control
    access_control_model: str = Field(
        default="RBAC",
        description="Access control model (RBAC/ABAC/etc)",
    )
    default_action: str = Field(
        default="deny", description="Default action (allow/deny)"
    )

    # Security rules
    rules: list[ModelSecurityRule] = Field(
        default_factory=list,
        description="Security rules",
    )

    # Authentication requirements
    require_authentication: bool = Field(
        default=True, description="Require authentication"
    )
    allowed_auth_methods: list[str] = Field(
        default_factory=list,
        description="Allowed authentication methods",
    )
    require_mfa: bool = Field(
        default=False, description="Require multi-factor authentication"
    )

    # Session management
    session_timeout_minutes: int | None = Field(
        default=30, description="Session timeout"
    )
    max_sessions_per_user: int | None = Field(
        default=5,
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
    valid_from: datetime | None = Field(default=None, description="Policy valid from")
    valid_until: datetime | None = Field(default=None, description="Policy valid until")
    time_restrictions: ModelTimeRestrictions | None = Field(
        default=None,
        description="Time-based access restrictions",
    )

    # Compliance tags
    compliance_frameworks: list[str] = Field(
        default_factory=list,
        description="Compliance frameworks (SOC2, HIPAA, etc)",
    )
    data_classification: str | None = Field(
        default=None,
        description="Data classification level",
    )

    model_config = ConfigDict()

    def to_dict(self) -> ModelSecurityPolicyData:
        """Convert to data container for current standards."""
        # Convert dict to ModelTypedMapping following ONEX pattern
        from omnibase_core.models.common.model_typed_mapping import ModelTypedMapping

        typed_mapping = ModelTypedMapping()
        for key, value in self.model_dump(exclude_none=True).items():
            typed_mapping.set_value(key, value)

        return ModelSecurityPolicyData(typed_data=typed_mapping)

    @classmethod
    def from_dict(cls, data: ModelSecurityPolicyData) -> "ModelSecurityPolicy":
        """Create from data container for easy migration."""
        # Convert ModelTypedMapping to dict for ** unpacking
        data_dict = data.typed_data.to_python_dict()
        return cls(**data_dict)

    @field_serializer("created_at", "updated_at", "valid_from", "valid_until")
    def serialize_datetime(self, value: Any) -> Any:
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
