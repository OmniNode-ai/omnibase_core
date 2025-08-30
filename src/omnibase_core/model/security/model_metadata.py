"""Model metadata imports for security models."""

from .model_evaluation_context import ModelEvaluationContext
from .model_policy_evaluation_details import ModelPolicyEvaluationDetails

# Import aliases for backward compatibility with existing code
model_evaluation_context = ModelEvaluationContext
model_policy_evaluation_details = ModelPolicyEvaluationDetails

# Placeholder models for other missing imports - these need to be created
# For now, using basic models to prevent import errors

from pydantic import BaseModel, Field

# Import from separate file to break circular imports
from .model_evaluation_models import (
    ModelAuthorizationEvaluation,
    ModelComplianceEvaluation,
    ModelSignatureEvaluation,
)


class ModelSignatureRequirements(BaseModel):
    """Signature requirements model."""

    minimum_signatures: int = Field(
        default=1,
        description="Minimum number of signatures required",
    )
    required_algorithms: list[str] = Field(
        default_factory=list,
        description="Required signature algorithms",
    )
    trusted_nodes: set[str] = Field(
        default_factory=set,
        description="Set of trusted node IDs",
    )
    compliance_tags: list[str] = Field(
        default_factory=list,
        description="Required compliance tags",
    )


class ModelVerificationResult(BaseModel):
    """Verification result model."""

    is_valid: bool = Field(default=False, description="Whether verification passed")
    errors: list[str] = Field(default_factory=list, description="Verification errors")
    warnings: list[str] = Field(
        default_factory=list,
        description="Verification warnings",
    )
    trust_level: str = Field(
        default="untrusted",
        description="Trust level of verification",
    )


class ModelComplianceStatus(BaseModel):
    """Compliance status model."""

    frameworks: list[str] = Field(
        default_factory=list,
        description="Compliance frameworks",
    )
    classification: str | None = Field(None, description="Data classification")
    audit_trail_complete: bool = Field(
        default=False,
        description="Whether audit trail is complete",
    )


class ModelEnforcementAction(BaseModel):
    """Enforcement action model."""

    timestamp: str = Field(..., description="Action timestamp")
    envelope_id: str = Field(..., description="Envelope ID")
    policy_id: str = Field(..., description="Policy ID")
    decision: str = Field(..., description="Enforcement decision")
    confidence: float = Field(..., description="Decision confidence")
    reasons: list[str] = Field(default_factory=list, description="Decision reasons")
    enforcement_actions: list[str] = Field(
        default_factory=list,
        description="Actions taken",
    )
    evaluation_time_ms: float = Field(
        ...,
        description="Evaluation time in milliseconds",
    )


class ModelVerificationDetails(BaseModel):
    """Detailed verification information for signature verification."""

    certificate_validation: dict[str, str | None] = Field(
        default_factory=dict,
        description="Certificate validation details",
    )
    signature_algorithm: str = Field(default="", description="Signature algorithm used")
    certificate_id: str = Field(default="", description="Certificate identifier")
    security_level: str = Field(
        default="basic",
        description="Security level assessment",
    )
    compliance_level: str = Field(
        default="basic",
        description="Compliance level assessment",
    )
    trust_level: str = Field(default="untrusted", description="Trust level assessment")
    verification_time_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description="Time breakdown for verification steps",
    )
    performance_optimizations: dict[str, bool] = Field(
        default_factory=dict,
        description="Performance optimization flags",
    )


class ModelTimeBreakdown(BaseModel):
    """Time breakdown for signature verification operations."""

    total_time_ms: float = Field(
        default=0.0,
        description="Total verification time in milliseconds",
    )
    certificate_validation_ms: float = Field(
        default=0.0,
        description="Certificate validation time in milliseconds",
    )
    signature_verification_ms: float = Field(
        default=0.0,
        description="Signature verification time in milliseconds",
    )
    chain_validation_ms: float = Field(
        default=0.0,
        description="Chain validation time in milliseconds",
    )
    cache_lookup_ms: float = Field(
        default=0.0,
        description="Cache lookup time in milliseconds",
    )
    network_operations_ms: float = Field(
        default=0.0,
        description="Network operations time in milliseconds",
    )


class ModelPerformanceOptimizations(BaseModel):
    """Performance optimization settings and status."""

    certificate_cached: bool = Field(
        default=False,
        description="Whether certificate was cached",
    )
    signature_cached: bool = Field(
        default=False,
        description="Whether signature was cached",
    )
    trusted_node: bool = Field(
        default=False,
        description="Whether node is in trusted list",
    )
    parallel_verification: bool = Field(
        default=False,
        description="Whether parallel verification was used",
    )
    fast_path: bool = Field(
        default=False,
        description="Whether fast verification path was used",
    )


class ModelVerificationMetrics(BaseModel):
    """Verification performance metrics."""

    total_verifications: int = Field(
        default=0,
        description="Total number of verifications performed",
    )
    cache_hit_rate: float = Field(default=0.0, description="Cache hit rate percentage")
    average_verification_time_ms: float = Field(
        default=0.0,
        description="Average verification time in milliseconds",
    )
    fastest_verification_ms: float = Field(
        default=0.0,
        description="Fastest verification time in milliseconds",
    )
    slowest_verification_ms: float = Field(
        default=0.0,
        description="Slowest verification time in milliseconds",
    )


class ModelCacheSizes(BaseModel):
    """Cache size information for monitoring."""

    signature_cache_size: int = Field(
        default=0,
        description="Number of cached signature results",
    )
    certificate_cache_size: int = Field(
        default=0,
        description="Number of cached certificate validations",
    )
    content_hash_cache_size: int = Field(
        default=0,
        description="Number of cached content hashes",
    )
    max_cache_size: int = Field(default=1000, description="Maximum cache size limit")


class ModelTrustedNodesInfo(BaseModel):
    """Information about trusted nodes configuration."""

    total_trusted_nodes: int = Field(
        default=0,
        description="Total number of trusted nodes",
    )
    high_trust_nodes: int = Field(default=0, description="Number of high trust nodes")
    trusted_node_ids: list[str] = Field(
        default_factory=list,
        description="List of trusted node identifiers",
    )
    high_trust_node_ids: list[str] = Field(
        default_factory=list,
        description="List of high trust node identifiers",
    )


class ModelPerformanceSettings(BaseModel):
    """Performance configuration settings."""

    cache_ttl_seconds: int = Field(
        default=3600,
        description="Cache time-to-live in seconds",
    )
    max_verification_time_ms: int = Field(
        default=15000,
        description="Maximum verification time in milliseconds",
    )
    parallel_verification_enabled: bool = Field(
        default=True,
        description="Whether parallel verification is enabled",
    )
    enable_caching: bool = Field(default=True, description="Whether caching is enabled")
    max_parallel_verifications: int = Field(
        default=10,
        description="Maximum parallel verifications",
    )


# Aliases for backward compatibility
model_signature_evaluation = ModelSignatureEvaluation
model_compliance_evaluation = ModelComplianceEvaluation
model_authorization_evaluation = ModelAuthorizationEvaluation
model_signature_requirements = ModelSignatureRequirements
model_verification_result = ModelVerificationResult
model_compliance_status = ModelComplianceStatus
model_enforcement_action = ModelEnforcementAction
model_verification_details = ModelVerificationDetails
model_time_breakdown = ModelTimeBreakdown
model_performance_optimizations = ModelPerformanceOptimizations
model_verification_metrics = ModelVerificationMetrics
model_cache_sizes = ModelCacheSizes
model_trusted_nodes_info = ModelTrustedNodesInfo
model_performance_settings = ModelPerformanceSettings
