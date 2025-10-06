"""ModelEvaluationContext: Context for policy evaluation."""

from uuid import UUID

from pydantic import BaseModel, Field


class ModelEvaluationContext(BaseModel):
    """Context information for policy evaluation."""

    envelope_id: UUID = Field(default=..., description="Envelope identifier")
    source_node_id: UUID = Field(default=..., description="Source node identifier")
    destination: str | None = Field(default=None, description="Final destination")
    hop_count: int = Field(default=0, description="Current hop count", ge=0)
    is_encrypted: bool = Field(
        default=False, description="Whether payload is encrypted"
    )
    signature_count: int = Field(default=0, description="Number of signatures", ge=0)
    trust_level: str | None = Field(default=None, description="Required trust level")
    compliance_frameworks: list[str] = Field(
        default_factory=list,
        description="Required compliance frameworks",
    )
    classification: str | None = Field(default=None, description="Data classification")
    contains_pii: bool = Field(default=False, description="Contains PII data")
    contains_phi: bool = Field(default=False, description="Contains PHI data")
    contains_financial: bool = Field(
        default=False, description="Contains financial data"
    )
    user_id: UUID | None = Field(default=None, description="User identifier")
    username: str | None = Field(default=None, description="Username")
    roles: list[str] = Field(default_factory=list, description="User roles")
    groups: list[str] = Field(default_factory=list, description="User groups")
    mfa_verified: bool = Field(default=False, description="MFA verification status")
    trust_level_user: str | None = Field(default=None, description="User trust level")
    timestamp: str = Field(default=..., description="Evaluation timestamp")
    policy_id: UUID | None = Field(
        default=None, description="Specific policy ID to use"
    )
