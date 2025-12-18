"""
Security Summary Models.

Strongly-typed summary models for security domain return values.
These models replace dict[str, Any] return types with proper Pydantic models.
"""

from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import TypedDictSignatureOptionalParams

# Type alias for use in this module
SignatureOptionalParams = TypedDictSignatureOptionalParams


class ModelDetectionConfigSummary(BaseModel):
    """Summary of detection configuration settings."""

    config_id: UUID = Field(description="Configuration ID")
    config_name: str = Field(description="Configuration name")
    enabled_rulesets_count: int = Field(description="Number of enabled rulesets")
    global_confidence_threshold: float = Field(
        description="Global confidence threshold"
    )
    max_document_size_mb: int = Field(description="Maximum document size in MB")
    parallel_workers: int = Field(description="Number of parallel workers")
    supported_file_types: list[str] = Field(description="Supported file types")
    features: "ModelDetectionFeatures" = Field(description="Detection features")


class ModelDetectionFeatures(BaseModel):
    """Detection feature flags."""

    false_positive_reduction: bool = Field(
        description="False positive reduction enabled"
    )
    context_analysis: bool = Field(description="Context analysis enabled")
    ml_detection: bool = Field(description="ML detection enabled")
    audit_logging: bool = Field(description="Audit logging enabled")


class ModelProcessingSummary(BaseModel):
    """Summary of node signature processing."""

    node_id: UUID = Field(description="Node ID")
    operation: str = Field(description="Operation performed")
    hop_index: int = Field(description="Hop index in chain")
    timestamp: str = Field(description="Timestamp ISO format")
    processing_time_ms: int | None = Field(
        default=None, description="Processing time in ms"
    )
    signature_time_ms: int | None = Field(
        default=None, description="Signature time in ms"
    )
    has_errors: bool = Field(description="Whether errors occurred")
    has_warnings: bool = Field(description="Whether warnings occurred")
    error_count: int = Field(description="Number of warnings/errors")


class ModelComplianceInfoSummary(BaseModel):
    """Summary of compliance information."""

    framework_count: int = Field(description="Number of compliance frameworks")
    classification: str = Field(description="Data classification level")
    has_pii: bool = Field(description="Contains PII")
    has_phi: bool = Field(description="Contains PHI")
    has_financial: bool = Field(description="Contains financial data")
    has_sensitive_data: bool = Field(description="Has any sensitive data")
    risk_level: str = Field(description="Risk level")


class ModelSecurityControlsSummary(BaseModel):
    """Summary of security controls."""

    encryption_enabled: bool = Field(description="Encryption enabled")
    signatures_required: bool = Field(description="Signatures required")
    signature_valid: bool = Field(description="Signature is valid")
    signature_trusted: bool = Field(description="Signature is trusted")
    has_recent_events: bool = Field(description="Has recent security events")
    security_events_count: int = Field(description="Number of security events")


class ModelComprehensiveSecuritySummary(BaseModel):
    """Comprehensive security summary with all details."""

    envelope_id: UUID = Field(description="Envelope ID")
    security_level: str = Field(description="Security level")
    security_score: float = Field(description="Security score 0-100")
    risk_level: str = Field(description="Risk level")
    controls: ModelSecurityControlsSummary = Field(description="Security controls")
    signature_chain: "ModelChainInfoSummary" = Field(description="Signature chain info")
    compliance: ModelComplianceInfoSummary = Field(description="Compliance info")
    authorization: "ModelAuthorizationInfoSummary" = Field(
        description="Authorization info"
    )
    last_security_event: "ModelSecurityEventInfo | None" = Field(
        default=None, description="Last security event"
    )


class ModelSecurityPostureSummary(BaseModel):
    """Security posture validation result."""

    is_secure: bool = Field(description="Whether security posture is secure")
    issue_count: int = Field(description="Number of issues")
    issues: list[str] = Field(description="List of issues")
    security_score: float = Field(description="Security score")


class ModelComplianceStatusSummary(BaseModel):
    """Summary of compliance evaluation status."""

    meets_requirements: bool = Field(description="Whether requirements are met")
    violation_count: int = Field(description="Number of violations")
    warning_count: int = Field(description="Number of warnings")
    framework_count: int = Field(description="Number of frameworks")
    compliant_frameworks: int = Field(description="Number of compliant frameworks")


class ModelSignatureEvaluationSummary(BaseModel):
    """Summary of signature evaluation."""

    is_valid: bool = Field(description="Whether signature is valid")
    meets_requirements: bool = Field(description="Whether requirements are met")
    violation_count: int = Field(description="Number of violations")
    warning_count: int = Field(description="Number of warnings")


class ModelAuthorizationEvaluationSummary(BaseModel):
    """Summary of authorization evaluation."""

    meets_requirements: bool = Field(description="Whether requirements are met")
    violation_count: int = Field(description="Number of violations")
    warning_count: int = Field(description="Number of warnings")
    is_authorized: bool = Field(description="Whether authorized")


class ModelAuthorizationInfoSummary(BaseModel):
    """Summary of authorization information."""

    role_count: int = Field(description="Number of roles")
    node_count: int = Field(description="Number of nodes")
    clearance_required: bool = Field(description="Whether clearance is required")
    clearance_level: str = Field(description="Clearance level")
    authorized_roles: list[str] = Field(description="Authorized roles")
    authorized_nodes: list[str] = Field(description="Authorized nodes")


class ModelChainInfoSummary(BaseModel):
    """Summary of signature chain information."""

    chain_id: UUID = Field(description="Chain ID")
    envelope_id: UUID = Field(description="Envelope ID")
    signature_count: int = Field(description="Number of signatures")
    unique_signers: int = Field(description="Number of unique signers")
    signer_efficiency: float = Field(description="Signer efficiency ratio")
    operation_count: int = Field(description="Number of operations")
    algorithm_count: int = Field(description="Number of algorithms")
    compliance_count: int = Field(description="Number of compliance frameworks")
    is_valid: bool = Field(description="Whether chain is valid")
    is_trusted: bool = Field(description="Whether chain is trusted")
    has_complete_route: bool = Field(description="Whether route is complete")
    validation_status: str = Field(description="Validation status")
    trust_level: str = Field(description="Trust level")


class ModelDetectionPatternSummary(BaseModel):
    """Summary of detection pattern."""

    pattern_id: UUID = Field(description="Pattern ID")
    pattern_name: str = Field(description="Pattern name")
    detection_type: str = Field(description="Detection type value")
    sensitivity_level: str = Field(description="Sensitivity level value")
    enabled: bool = Field(description="Whether pattern is enabled")
    supported_languages: list[str] = Field(description="Supported language values")
    confidence_threshold: float = Field(description="Confidence threshold")


class ModelDetectionRuleSetSummary(BaseModel):
    """Summary of detection ruleset."""

    ruleset_id: UUID = Field(description="Ruleset ID")
    ruleset_name: str = Field(description="Ruleset name")
    version: ModelSemVer = Field(description="Ruleset version")
    pattern_count: int = Field(description="Total pattern count")
    enabled_pattern_count: int = Field(description="Enabled pattern count")
    detection_types: list[str] = Field(description="Detection type values")
    supported_languages: list[str] = Field(description="Supported language values")
    tags: list[str] = Field(description="Tags")


class ModelSecurityEventInfo(BaseModel):
    """Security event information summary."""

    event_id: UUID = Field(description="Event ID")
    event_type: str = Field(description="Event type")
    timestamp: str = Field(description="Timestamp")
    envelope_id: UUID = Field(description="Envelope ID")
    severity: str = Field(description="Event severity")
    is_recent: bool = Field(description="Whether event is recent")


class ModelEventTimeRange(BaseModel):
    """Time range for events."""

    earliest: str = Field(description="Earliest timestamp ISO format")
    latest: str = Field(description="Latest timestamp ISO format")


class ModelEventStatistics(BaseModel):
    """Statistics about security events."""

    total_events: int = Field(description="Total number of events")
    event_types: dict[str, int] = Field(
        default_factory=dict, description="Count by event type"
    )
    severity_distribution: dict[str, int] = Field(
        default_factory=dict, description="Count by severity"
    )
    users_involved: list[UUID] = Field(
        default_factory=list, description="Users involved"
    )
    nodes_involved: list[UUID] = Field(
        default_factory=list, description="Nodes involved"
    )
    time_range: ModelEventTimeRange | None = Field(
        default=None, description="Time range of events"
    )


class ModelBackendConfigData(BaseModel):
    """Backend configuration data for validation."""

    dotenv_path: str | None = Field(default=None, description="Dotenv file path")
    auto_load_dotenv: str | None = Field(
        default=None, description="Auto load dotenv flag"
    )
    env_prefix: str | None = Field(
        default=None, description="Environment variable prefix"
    )
    vault_url: str | None = Field(default=None, description="Vault URL")
    vault_token: str | None = Field(default=None, description="Vault token")
    vault_namespace: str | None = Field(default=None, description="Vault namespace")
    vault_path: str | None = Field(default=None, description="Vault path")
    namespace: str | None = Field(default=None, description="Kubernetes namespace")
    secret_name: str | None = Field(default=None, description="Kubernetes secret name")
    file_path: str | None = Field(default=None, description="File path")
    encryption_key: str | None = Field(default=None, description="Encryption key")


# Forward reference updates
ModelDetectionConfigSummary.model_rebuild()
ModelComprehensiveSecuritySummary.model_rebuild()
ModelDetectionRuleSetSummary.model_rebuild()


__all__ = [
    "ModelAuthorizationEvaluationSummary",
    "ModelAuthorizationInfoSummary",
    "ModelBackendConfigData",
    "ModelChainInfoSummary",
    "ModelComplianceInfoSummary",
    "ModelComplianceStatusSummary",
    "ModelComprehensiveSecuritySummary",
    "ModelDetectionConfigSummary",
    "ModelDetectionFeatures",
    "ModelDetectionPatternSummary",
    "ModelDetectionRuleSetSummary",
    "ModelEventStatistics",
    "ModelEventTimeRange",
    "ModelProcessingSummary",
    "ModelSecurityControlsSummary",
    "ModelSecurityEventInfo",
    "ModelSecurityPostureSummary",
    "ModelSignatureEvaluationSummary",
    "SignatureOptionalParams",
]
