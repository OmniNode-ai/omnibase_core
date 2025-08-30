"""
ModelPolicyContext: Context for policy evaluation.

This model represents the context used for evaluating trust policies
against secure envelopes.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelPolicyContext(BaseModel):
    """Context for policy evaluation."""

    envelope_id: str = Field(..., description="Envelope identifier")
    source_node_id: str = Field(..., description="Source node ID")
    current_hop_count: int = Field(..., description="Current hop count")
    operation_type: str = Field(default="routing", description="Type of operation")
    is_encrypted: bool = Field(..., description="Whether payload is encrypted")

    # Compliance information
    frameworks: List[str] = Field(..., description="Compliance frameworks")
    classification: str = Field(..., description="Data classification")
    retention_period_days: Optional[int] = Field(None, description="Retention period")
    jurisdiction: Optional[str] = Field(None, description="Legal jurisdiction")
    consent_required: bool = Field(..., description="Whether consent is required")
    audit_level: str = Field(..., description="Audit level required")
    contains_pii: bool = Field(..., description="Contains PII")
    contains_phi: bool = Field(..., description="Contains PHI")
    contains_financial: bool = Field(..., description="Contains financial data")
    export_controlled: bool = Field(..., description="Subject to export controls")

    # Security context
    user_id: Optional[str] = Field(None, description="User identifier")
    roles: List[str] = Field(default_factory=list, description="User roles")
    security_clearance: Optional[str] = Field(None, description="Security clearance")
    trust_level: Optional[int] = Field(None, description="Trust level")
