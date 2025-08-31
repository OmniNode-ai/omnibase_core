"""
Document audit result models for comprehensive document analysis and reporting.

Defines data structures for audit results, quality scoring, compliance reporting,
and AI-powered document analysis within the ONEX document management system.
"""

from datetime import datetime
from enum import Enum

from pydantic import Field, validator

from omnibase_core.model.core.model_onex_base_state import ModelOnexInputState
from omnibase_core.model.docs.model_document_freshness import EnumDocumentType
from omnibase_core.model.docs.model_document_lifecycle import EnumDocumentCategory


class EnumAuditType(str, Enum):
    """Types of document audits that can be performed."""

    FRESHNESS_AUDIT = "freshness_audit"
    QUALITY_AUDIT = "quality_audit"
    COMPLIANCE_AUDIT = "compliance_audit"
    DEPENDENCY_AUDIT = "dependency_audit"
    CONTENT_AUDIT = "content_audit"
    AI_POWERED_AUDIT = "ai_powered_audit"
    SECURITY_AUDIT = "security_audit"
    ACCESSIBILITY_AUDIT = "accessibility_audit"
    COMPREHENSIVE_AUDIT = "comprehensive_audit"


class EnumAuditSeverity(str, Enum):
    """Severity levels for audit findings."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EnumAuditStatus(str, Enum):
    """Status of audit execution."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class ModelAuditFinding(ModelOnexInputState):
    """Individual finding from a document audit."""

    finding_id: str = Field(..., description="Unique identifier for this finding")
    audit_type: EnumAuditType = Field(
        ...,
        description="Type of audit that generated this finding",
    )
    severity: EnumAuditSeverity = Field(
        ...,
        description="Severity level of this finding",
    )

    # Finding details
    title: str = Field(..., description="Short title describing the finding")
    description: str = Field(..., description="Detailed description of the finding")
    category: str = Field(
        ...,
        description="Category of finding (structure, content, format, etc.)",
    )

    # Location information
    document_path: str = Field(
        ...,
        description="Path to the document with this finding",
    )
    line_number: int | None = Field(
        None,
        description="Line number where finding was detected",
    )
    section: str | None = Field(
        None,
        description="Document section where finding was detected",
    )
    context: str | None = Field(
        None,
        description="Surrounding context for the finding",
    )

    # Remediation
    recommendation: str = Field(
        ...,
        description="Recommended action to address this finding",
    )
    estimated_effort_hours: float | None = Field(
        None,
        description="Estimated effort to fix",
    )
    auto_fixable: bool = Field(
        default=False,
        description="Whether this can be automatically fixed",
    )

    # AI analysis (if applicable)
    ai_confidence: float | None = Field(
        None,
        description="AI confidence in this finding (0.0-1.0)",
    )
    ai_reasoning: str | None = Field(
        None,
        description="AI reasoning for this finding",
    )

    # Tracking
    detected_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When finding was detected",
    )
    resolved: bool = Field(
        default=False,
        description="Whether finding has been resolved",
    )
    resolved_at: datetime | None = Field(
        None,
        description="When finding was resolved",
    )

    @validator("ai_confidence")
    def validate_ai_confidence(self, v):
        if v is not None and not 0.0 <= v <= 1.0:
            msg = "AI confidence must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ModelQualityMetrics(ModelOnexInputState):
    """Quality metrics for document assessment."""

    # Content quality
    completeness_score: float = Field(
        ...,
        description="How complete the documentation is (0.0-1.0)",
    )
    accuracy_score: float = Field(..., description="Accuracy of information (0.0-1.0)")
    clarity_score: float = Field(..., description="Clarity and readability (0.0-1.0)")
    currency_score: float = Field(
        ...,
        description="How up-to-date the content is (0.0-1.0)",
    )

    # Structure quality
    organization_score: float = Field(
        ...,
        description="Document organization and structure (0.0-1.0)",
    )
    formatting_score: float = Field(
        ...,
        description="Formatting consistency and quality (0.0-1.0)",
    )
    navigation_score: float = Field(
        ...,
        description="Navigation and linking quality (0.0-1.0)",
    )

    # Technical quality
    code_examples_score: float = Field(
        default=1.0,
        description="Quality of code examples (0.0-1.0)",
    )
    technical_accuracy_score: float = Field(
        default=1.0,
        description="Technical accuracy (0.0-1.0)",
    )

    # Overall metrics
    overall_quality_score: float = Field(
        ...,
        description="Overall quality score (0.0-1.0)",
    )
    quality_trend: str = Field(
        default="stable",
        description="Quality trend (improving, stable, declining)",
    )

    # Benchmarking
    peer_comparison_score: float | None = Field(
        None,
        description="Score compared to similar documents",
    )
    industry_standard_score: float | None = Field(
        None,
        description="Score against industry standards",
    )

    @validator(
        "completeness_score",
        "accuracy_score",
        "clarity_score",
        "currency_score",
        "organization_score",
        "formatting_score",
        "navigation_score",
        "code_examples_score",
        "technical_accuracy_score",
        "overall_quality_score",
        "peer_comparison_score",
        "industry_standard_score",
    )
    def validate_quality_scores(self, v):
        if v is not None and not 0.0 <= v <= 1.0:
            msg = "Quality score must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ModelComplianceMetrics(ModelOnexInputState):
    """Compliance metrics for document standards adherence."""

    # Standards compliance
    style_guide_compliance: float = Field(
        ...,
        description="Adherence to style guide (0.0-1.0)",
    )
    template_compliance: float = Field(
        ...,
        description="Adherence to document templates (0.0-1.0)",
    )
    metadata_compliance: float = Field(
        ...,
        description="Required metadata presence (0.0-1.0)",
    )

    # ONEX-specific compliance
    onex_standards_compliance: float = Field(
        ...,
        description="ONEX documentation standards compliance (0.0-1.0)",
    )
    contract_yaml_compliance: float = Field(
        default=1.0,
        description="Contract YAML compliance for nodes (0.0-1.0)",
    )
    architecture_compliance: float = Field(
        default=1.0,
        description="Architecture documentation compliance (0.0-1.0)",
    )

    # Accessibility compliance
    accessibility_score: float = Field(
        default=1.0,
        description="Accessibility compliance (0.0-1.0)",
    )
    alt_text_coverage: float = Field(
        default=1.0,
        description="Alt text coverage for images (0.0-1.0)",
    )

    # Security compliance
    sensitive_info_score: float = Field(
        default=1.0,
        description="No sensitive information exposed (0.0-1.0)",
    )
    credential_exposure_score: float = Field(
        default=1.0,
        description="No credentials exposed (0.0-1.0)",
    )

    # Overall compliance
    overall_compliance_score: float = Field(
        ...,
        description="Overall compliance score (0.0-1.0)",
    )
    compliance_issues_count: int = Field(
        default=0,
        description="Number of compliance issues found",
    )
    critical_compliance_issues: int = Field(
        default=0,
        description="Number of critical compliance issues",
    )

    @validator(
        "style_guide_compliance",
        "template_compliance",
        "metadata_compliance",
        "onex_standards_compliance",
        "contract_yaml_compliance",
        "architecture_compliance",
        "accessibility_score",
        "alt_text_coverage",
        "sensitive_info_score",
        "credential_exposure_score",
        "overall_compliance_score",
    )
    def validate_compliance_scores(self, v):
        if not 0.0 <= v <= 1.0:
            msg = "Compliance score must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ModelDocumentAuditResult(ModelOnexInputState):
    """Comprehensive audit result for a single document."""

    audit_id: str = Field(..., description="Unique identifier for this audit")
    document_path: str = Field(..., description="Path to the audited document")
    audit_type: EnumAuditType = Field(..., description="Type of audit performed")
    audit_status: EnumAuditStatus = Field(..., description="Status of the audit")

    # Timing
    audit_started_at: datetime = Field(..., description="When audit started")
    audit_completed_at: datetime | None = Field(
        None,
        description="When audit completed",
    )
    audit_duration_ms: int = Field(
        default=0,
        description="Audit duration in milliseconds",
    )

    # Document metadata
    document_type: EnumDocumentType = Field(..., description="Type of document audited")
    document_category: EnumDocumentCategory = Field(
        ...,
        description="Category of document",
    )
    document_size_bytes: int = Field(..., description="Size of document in bytes")
    document_line_count: int = Field(
        default=0,
        description="Number of lines in document",
    )

    # Audit results
    findings: list[ModelAuditFinding] = Field(
        default_factory=list,
        description="All findings from the audit",
    )
    quality_metrics: ModelQualityMetrics | None = Field(
        None,
        description="Quality assessment metrics",
    )
    compliance_metrics: ModelComplianceMetrics | None = Field(
        None,
        description="Compliance assessment metrics",
    )

    # Summary statistics
    total_findings: int = Field(default=0, description="Total number of findings")
    critical_findings: int = Field(default=0, description="Number of critical findings")
    high_findings: int = Field(
        default=0,
        description="Number of high severity findings",
    )
    medium_findings: int = Field(
        default=0,
        description="Number of medium severity findings",
    )
    low_findings: int = Field(default=0, description="Number of low severity findings")
    info_findings: int = Field(
        default=0,
        description="Number of informational findings",
    )

    # Overall assessment
    overall_score: float = Field(..., description="Overall audit score (0.0-1.0)")
    pass_threshold: float = Field(
        default=0.7,
        description="Minimum score to pass audit",
    )
    audit_passed: bool = Field(..., description="Whether document passed the audit")

    # Recommendations
    priority_actions: list[str] = Field(
        default_factory=list,
        description="High-priority recommended actions",
    )
    estimated_fix_effort_hours: float = Field(
        default=0.0,
        description="Estimated total effort to address findings",
    )
    next_audit_recommended_date: datetime | None = Field(
        None,
        description="When next audit is recommended",
    )

    # AI analysis (if applicable)
    ai_analysis_performed: bool = Field(
        default=False,
        description="Whether AI analysis was performed",
    )
    ai_overall_assessment: str | None = Field(
        None,
        description="AI's overall assessment of the document",
    )
    ai_improvement_suggestions: list[str] = Field(
        default_factory=list,
        description="AI-generated improvement suggestions",
    )

    @validator("overall_score", "pass_threshold")
    def validate_scores(self, v):
        if not 0.0 <= v <= 1.0:
            msg = "Score must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ModelBatchAuditResult(ModelOnexInputState):
    """Result of a batch audit operation across multiple documents."""

    batch_audit_id: str = Field(
        ...,
        description="Unique identifier for this batch audit",
    )
    audit_type: EnumAuditType = Field(..., description="Type of audit performed")
    audit_scope: str = Field(..., description="Scope of the batch audit")

    # Timing
    batch_started_at: datetime = Field(..., description="When batch audit started")
    batch_completed_at: datetime | None = Field(
        None,
        description="When batch audit completed",
    )
    total_duration_ms: int = Field(
        default=0,
        description="Total duration in milliseconds",
    )

    # Scope and progress
    total_documents_targeted: int = Field(
        ...,
        description="Total documents targeted for audit",
    )
    documents_successfully_audited: int = Field(
        default=0,
        description="Documents successfully audited",
    )
    documents_failed_audit: int = Field(
        default=0,
        description="Documents that failed to audit",
    )
    documents_skipped: int = Field(default=0, description="Documents skipped")

    # Individual results
    document_results: list[ModelDocumentAuditResult] = Field(
        default_factory=list,
        description="Results for each document",
    )

    # Aggregate statistics
    total_findings_across_all_docs: int = Field(
        default=0,
        description="Total findings across all documents",
    )
    average_quality_score: float = Field(
        default=0.0,
        description="Average quality score across documents",
    )
    average_compliance_score: float = Field(
        default=0.0,
        description="Average compliance score",
    )
    documents_passed_audit: int = Field(
        default=0,
        description="Number of documents that passed audit",
    )

    # Distribution of findings by severity
    critical_findings_total: int = Field(
        default=0,
        description="Total critical findings",
    )
    high_findings_total: int = Field(
        default=0,
        description="Total high severity findings",
    )
    medium_findings_total: int = Field(
        default=0,
        description="Total medium severity findings",
    )
    low_findings_total: int = Field(
        default=0,
        description="Total low severity findings",
    )

    # Top issues
    most_common_findings: list[dict] = Field(
        default_factory=list,
        description="Most frequently occurring findings",
    )
    documents_requiring_urgent_attention: list[str] = Field(
        default_factory=list,
        description="Documents needing urgent fixes",
    )

    # Recommendations and insights
    overall_recommendations: list[str] = Field(
        default_factory=list,
        description="Overall recommendations for the document set",
    )
    improvement_priorities: list[str] = Field(
        default_factory=list,
        description="Prioritized improvement areas",
    )
    estimated_total_fix_effort_hours: float = Field(
        default=0.0,
        description="Total estimated effort to address all findings",
    )

    # Trend analysis
    quality_trend_analysis: dict | None = Field(
        None,
        description="Quality trend analysis if historical data available",
    )
    compliance_trend_analysis: dict | None = Field(
        None,
        description="Compliance trend analysis",
    )

    # Performance metrics
    audit_performance_metrics: dict = Field(
        default_factory=dict,
        description="Performance metrics for the audit process",
    )

    @validator("average_quality_score", "average_compliance_score")
    def validate_average_scores(self, v):
        if not 0.0 <= v <= 1.0:
            msg = "Average score must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ModelAuditConfiguration(ModelOnexInputState):
    """Configuration for document audit operations."""

    # Audit scope
    enabled_audit_types: list[EnumAuditType] = Field(
        ...,
        description="Types of audits to perform",
    )
    document_type_filters: list[EnumDocumentType] = Field(
        default_factory=list,
        description="Document types to include (empty = all)",
    )
    directory_patterns: list[str] = Field(
        default_factory=list,
        description="Directory patterns to include",
    )
    excluded_patterns: list[str] = Field(
        default_factory=list,
        description="Patterns to exclude from audit",
    )

    # Quality thresholds
    minimum_quality_score: float = Field(
        default=0.7,
        description="Minimum acceptable quality score",
    )
    minimum_compliance_score: float = Field(
        default=0.8,
        description="Minimum acceptable compliance score",
    )

    # AI analysis settings
    enable_ai_analysis: bool = Field(
        default=True,
        description="Whether to enable AI-powered analysis",
    )
    ai_analysis_model: str = Field(
        default="phi3:latest",
        description="AI model to use for analysis",
    )
    ai_batch_size: int = Field(default=5, description="Batch size for AI analysis")
    ai_timeout_seconds: int = Field(
        default=120,
        description="Timeout for AI analysis per document",
    )

    # Performance settings
    max_concurrent_audits: int = Field(
        default=4,
        description="Maximum concurrent audit processes",
    )
    audit_timeout_seconds: int = Field(
        default=300,
        description="Timeout for individual document audits",
    )
    enable_caching: bool = Field(
        default=True,
        description="Whether to cache audit results",
    )
    cache_ttl_hours: int = Field(default=24, description="Cache time-to-live in hours")

    # Reporting settings
    generate_detailed_reports: bool = Field(
        default=True,
        description="Whether to generate detailed reports",
    )
    include_ai_reasoning: bool = Field(
        default=True,
        description="Include AI reasoning in reports",
    )
    export_formats: list[str] = Field(
        default_factory=lambda: ["json", "html"],
        description="Export formats for reports",
    )

    # Notification settings
    notify_on_critical_findings: bool = Field(
        default=True,
        description="Send notifications for critical findings",
    )
    notification_recipients: list[str] = Field(
        default_factory=list,
        description="Recipients for notifications",
    )

    @validator("minimum_quality_score", "minimum_compliance_score")
    def validate_minimum_scores(self, v):
        if not 0.0 <= v <= 1.0:
            msg = "Minimum score must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v
