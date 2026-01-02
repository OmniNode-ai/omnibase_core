"""
Tool security summary model.

Provides typed model for tool security configuration summary data.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.core.model_tool_security_assessment import (
    ModelToolSecurityAssessment,
)


class ModelToolSecuritySummary(BaseModel):
    """
    Typed model for tool security configuration summary.

    Replaces dict[str, Any] return from get_summary() in ModelToolSecurity.
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
    data_classification: str = Field(
        default="internal",
        description="Data classification level",
    )
    requires_network_access: bool = Field(
        default=False,
        description="Whether the tool requires network access",
    )
    external_endpoints: list[str] = Field(
        default_factory=list,
        description="List of external endpoints accessed",
    )
    security_profile_required: str = Field(
        default="SP0_BOOTSTRAP",
        description="Required security profile level",
    )
    security_assessment: ModelToolSecurityAssessment = Field(
        default_factory=ModelToolSecurityAssessment,
        description="Detailed security assessment",
    )


__all__ = ["ModelToolSecuritySummary"]
