"""
ModelBackendSecurityProfile: Security characteristics of secret backends.

This model represents the security profile of different secret backends.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_security_level import EnumSecurityLevel


class ModelBackendSecurityProfile(BaseModel):
    """Security characteristics of a secret backend."""

    encryption_at_rest: str = Field(
        default="none",
        description="Encryption at rest level: none, optional, strong",
        pattern=r"^(none|optional|configurable|strong)$",
    )

    encryption_in_transit: str = Field(
        default="none",
        description="Encryption in transit: none, tls",
        pattern=r"^(none|tls)$",
    )

    access_control: str = Field(
        default="os_level",
        description="Access control mechanism: os_level, file_permissions, rbac, policy_based",
        pattern=r"^(os_level|file_permissions|rbac|policy_based)$",
    )

    audit_logging: str = Field(
        default="none",
        description="Audit logging capability: none, version_control, cluster_level, comprehensive",
        pattern=r"^(none|version_control|cluster_level|comprehensive)$",
    )

    secret_rotation: str = Field(
        default="manual",
        description="Secret rotation capability: manual, automatic, manual_or_operator",
        pattern=r"^(manual|automatic|manual_or_operator)$",
    )

    security_level: EnumSecurityLevel = Field(
        default=EnumSecurityLevel.BASIC,
        description="Overall security level",
    )
