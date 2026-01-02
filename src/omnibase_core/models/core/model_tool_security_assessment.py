"""
Tool security assessment models.

Provides typed models for tool security assessment data,
replacing dict[str, Any] return types in ModelToolSecurity methods.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelToolSecurityAssessment(BaseModel):
    """
    Typed model for tool security assessment data.

    Replaces dict[str, Any] return from get_security_assessment() in ModelToolSecurity.
    """

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
        from_attributes=True,
    )

    processes_sensitive_data: bool = Field(
        default=False,
        description="Whether the tool processes sensitive data",
    )
    requires_network_access: bool = Field(
        default=False,
        description="Whether the tool requires network access",
    )
    accesses_external_endpoints: bool = Field(
        default=False,
        description="Whether the tool accesses external endpoints",
    )
    data_classification: str = Field(
        default="internal",
        description="Data classification level (public, internal, confidential, restricted)",
    )
    security_profile: str = Field(
        default="SP0_BOOTSTRAP",
        description="Required security profile level",
    )
    is_high_security: bool = Field(
        default=False,
        description="Whether high security profile is required",
    )
    is_bootstrap: bool = Field(
        default=False,
        description="Whether using bootstrap security profile",
    )
    external_endpoint_count: int = Field(
        default=0,
        description="Number of external endpoints accessed",
        ge=0,
    )
    risk_level: str = Field(
        default="low",
        description="Overall risk level (low, medium, high)",
    )


__all__ = ["ModelToolSecurityAssessment"]
