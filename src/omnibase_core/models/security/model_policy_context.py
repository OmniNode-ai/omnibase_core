from typing import Any

from pydantic import Field

"""
ModelPolicyContext: Context for policy evaluation.

This model represents the context used for evaluating trust policies
against secure envelopes.
"""

from pydantic import BaseModel, Field


class ModelPolicyContext(BaseModel):
    """Context for policy evaluation."""

    envelope_id: str = Field(default=..., description="Envelope identifier")
    source_node_id: str = Field(default=..., description="Source node ID")
    current_hop_count: int = Field(default=..., description="Current hop count")
    operation_type: str = Field(default="routing", description="Type of operation")
    is_encrypted: bool = Field(default=..., description="Whether payload is encrypted")

    # Compliance information
    frameworks: list[str] = Field(default=..., description="Compliance frameworks")
    classification: str = Field(default=..., description="Data classification")
    retention_period_days: int | None = Field(
        default=None, description="Retention period"
    )
    jurisdiction: str | None = Field(default=None, description="Legal jurisdiction")
    consent_required: bool = Field(
        default=..., description="Whether consent is required"
    )
    audit_level: str = Field(default=..., description="Audit level required")
    contains_pii: bool = Field(default=..., description="Contains PII")
    contains_phi: bool = Field(default=..., description="Contains PHI")
    contains_financial: bool = Field(default=..., description="Contains financial data")
    export_controlled: bool = Field(
        default=..., description="Subject to export controls"
    )

    # Security context
    user_id: str | None = Field(default=None, description="User identifier")
    roles: list[str] = Field(default_factory=list, description="User roles")
    security_clearance: str | None = Field(
        default=None, description="Security clearance"
    )
    trust_level: int | None = Field(default=None, description="Trust level")
