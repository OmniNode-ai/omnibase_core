"""
ModelSecuritySummary: Comprehensive security summary for reporting.

This model provides a structured summary of all security aspects
of a secure event envelope.
"""

from pydantic import BaseModel, Field


class ModelComplianceSummary(BaseModel):
    """Compliance information summary."""

    frameworks: list[str] = Field(..., description="Applicable compliance frameworks")
    classification: str = Field(..., description="Data classification level")
    contains_pii: bool = Field(
        ...,
        description="Contains personally identifiable information",
    )
    contains_phi: bool = Field(..., description="Contains protected health information")
    contains_financial: bool = Field(..., description="Contains financial data")


class ModelAuthorizationSummary(BaseModel):
    """Authorization requirements summary."""

    authorized_roles: list[str] = Field(..., description="Roles authorized to process")
    authorized_nodes: list[str] = Field(..., description="Nodes authorized to process")
    security_clearance_required: str | None = Field(
        None,
        description="Required security clearance",
    )


class ModelSignatureChainSummary(BaseModel):
    """Signature chain summary."""

    chain_id: str = Field(..., description="Chain identifier")
    envelope_id: str = Field(..., description="Envelope identifier")
    signature_count: int = Field(..., description="Total signatures")
    unique_signers: int = Field(..., description="Unique signers")
    operations: list[str] = Field(..., description="Operations performed")
    algorithms: list[str] = Field(..., description="Algorithms used")
    has_complete_route: bool = Field(..., description="Route completeness")
    validation_status: str = Field(..., description="Validation status")
    trust_level: str = Field(..., description="Trust level")
    created_at: str = Field(..., description="Creation timestamp")
    last_modified: str = Field(..., description="Last modification")
    chain_hash: str = Field(..., description="Chain hash (truncated)")
    compliance_frameworks: list[str] = Field(..., description="Compliance frameworks")


class ModelSecurityEventSummary(BaseModel):
    """Security event summary."""

    event_id: str = Field(..., description="Event identifier")
    event_type: str = Field(..., description="Event type")
    timestamp: str = Field(..., description="Event timestamp")
    envelope_id: str = Field(..., description="Envelope ID")
    # Additional fields from the actual event can be included as needed


class ModelSecuritySummary(BaseModel):
    """Comprehensive security summary for reporting."""

    envelope_id: str = Field(..., description="Envelope identifier")
    security_level: str = Field(..., description="Required security level")
    is_encrypted: bool = Field(..., description="Whether payload is encrypted")
    signature_required: bool = Field(..., description="Whether signatures are required")
    content_hash: str = Field(..., description="Content hash for integrity")
    signature_chain: ModelSignatureChainSummary = Field(
        ...,
        description="Signature chain summary",
    )
    compliance: ModelComplianceSummary = Field(
        ...,
        description="Compliance information",
    )
    authorization: ModelAuthorizationSummary = Field(
        ...,
        description="Authorization requirements",
    )
    security_events_count: int = Field(..., description="Number of security events")
    last_security_event: ModelSecurityEventSummary | None = Field(
        None,
        description="Most recent security event",
    )
