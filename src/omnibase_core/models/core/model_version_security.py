"""
Version Security Model - Tier 3 Metadata.

Pydantic model for version-specific security configuration.
"""

from pydantic import BaseModel, Field


class ModelVersionSecurity(BaseModel):
    """Version-specific security configuration."""

    security_context: dict[str, str] = Field(
        default_factory=dict,
        description="Security context requirements",
    )
    data_handling_declaration: dict[str, str] = Field(
        default_factory=dict,
        description="Data handling and classification",
    )
    audit_events: list[str] = Field(
        default_factory=list,
        description="Security audit events generated",
    )
    encryption_requirements: dict[str, str] = Field(
        default_factory=dict,
        description="Encryption requirements",
    )
    authentication_methods: list[str] = Field(
        default_factory=list,
        description="Supported authentication methods",
    )
