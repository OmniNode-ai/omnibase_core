from typing import Any

"""ModelEvaluationContext: Context for policy evaluation."""

from pydantic import BaseModel, Field


class ModelEvaluationContext(BaseModel):
    """Context information for policy evaluation."""

    envelope_id: str = Field(..., description="Envelope identifier")
    source_node_id: str = Field(..., description="Source node identifier")
    destination: str | None = Field(None, description="Final destination")
    hop_count: int = Field(0, description="Current hop count", ge=0)
    is_encrypted: bool = Field(False, description="Whether payload is encrypted")
    signature_count: int = Field(0, description="Number of signatures", ge=0)
    trust_level: str | None = Field(None, description="Required trust level")
    compliance_frameworks: list[str] = Field(
        default_factory=list,
        description="Required compliance frameworks",
    )
    classification: str | None = Field(None, description="Data classification")
    contains_pii: bool = Field(False, description="Contains PII data")
    contains_phi: bool = Field(False, description="Contains PHI data")
    contains_financial: bool = Field(False, description="Contains financial data")
    user_id: str | None = Field(None, description="User identifier")
    username: str | None = Field(None, description="Username")
    roles: list[str] = Field(default_factory=list, description="User roles")
    groups: list[str] = Field(default_factory=list, description="User groups")
    mfa_verified: bool = Field(False, description="MFA verification status")
    trust_level_user: str | None = Field(None, description="User trust level")
    timestamp: str = Field(..., description="Evaluation timestamp")
    policy_id: str | None = Field(None, description="Specific policy ID to use")
