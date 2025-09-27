"""
Pydantic models for intelligence document processing and API communication.

These models ensure proper serialization/deserialization and validation
for intelligence hooks, MCP requests, and service communication.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.metadata.model_semver import (
    ModelSemVer,
    parse_semver_from_string,
)


class IntelligenceDocumentType(str, Enum):
    """Types of intelligence documents"""

    INTELLIGENCE = "intelligence"
    CORRELATION = "correlation"
    SECURITY_ANALYSIS = "security_analysis"
    CODE_ANALYSIS = "code_analysis"


class AnalysisType(str, Enum):
    """Types of analysis performed"""

    ENHANCED_CODE_CHANGES_WITH_CORRELATION = "enhanced_code_changes_with_correlation"
    BASIC_CODE_CHANGES = "basic_code_changes"
    SECURITY_SCAN = "security_scan"
    PERFORMANCE_ANALYSIS = "performance_analysis"


class RiskLevel(str, Enum):
    """Risk assessment levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityStatus(str, Enum):
    """Security scan results"""

    CLEAN = "clean"
    WARNINGS = "warnings"
    ISSUES = "issues"
    CRITICAL = "critical"


# === Intelligence Document Structure Models ===


class IntelligenceMetadata(BaseModel):
    """Metadata for intelligence documents"""

    timestamp: datetime = Field(..., description="Analysis timestamp")
    repository: str = Field(..., description="Repository name")
    branch: str = Field(..., description="Git branch")
    commit: str = Field(..., description="Commit hash")
    author: str = Field(..., description="Commit author")
    hook_version: ModelSemVer = Field(..., description="Intelligence hook version")


class ChangeSummary(BaseModel):
    """Summary of code changes"""

    commit_message: str = Field(..., description="Git commit message")
    files_changed: int = Field(..., description="Number of files modified")
    lines_added: int = Field(0, description="Lines added")
    lines_removed: int = Field(0, description="Lines removed")
    security_status: SecurityStatus = Field(
        SecurityStatus.CLEAN, description="Security scan result"
    )


class ImpactAssessment(BaseModel):
    """Assessment of change impact"""

    coordination_required: bool = Field(
        False, description="Whether coordination is needed"
    )
    risk_level: RiskLevel = Field(RiskLevel.LOW, description="Overall risk level")
    affected_systems: List[str] = Field(
        default_factory=list, description="Systems that may be affected"
    )
    breaking_changes: List[str] = Field(
        default_factory=list, description="Potential breaking changes"
    )


class CrossRepositoryCorrelation(BaseModel):
    """Cross-repository correlation analysis"""

    enabled: bool = Field(
        True, description="Whether correlation analysis was performed"
    )
    correlation_id: UUID = Field(..., description="Unique correlation identifier")
    temporal_correlations: List[Dict[str, ModelSchemaValue]] = Field(
        default_factory=list, description="Time-based correlations"
    )
    semantic_correlations: List[Dict[str, ModelSchemaValue]] = Field(
        default_factory=list, description="Semantic correlations"
    )
    breaking_changes: List[Dict[str, ModelSchemaValue]] = Field(
        default_factory=list, description="Breaking change correlations"
    )
    impact_assessment: ImpactAssessment = Field(..., description="Impact assessment")


class SecurityAndPrivacy(BaseModel):
    """Security and privacy analysis"""

    sensitive_patterns: List[str] = Field(
        default_factory=list, description="Detected sensitive patterns"
    )
    security_score: float = Field(
        1.0, ge=0.0, le=1.0, description="Security confidence score"
    )
    privacy_concerns: List[str] = Field(
        default_factory=list, description="Privacy-related concerns"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Security recommendations"
    )


class TechnicalAnalysis(BaseModel):
    """Technical code analysis"""

    complexity_score: float = Field(0.0, ge=0.0, description="Code complexity score")
    quality_score: float = Field(1.0, ge=0.0, le=1.0, description="Code quality score")
    maintainability: str = Field("good", description="Maintainability assessment")
    test_coverage: Optional[float] = Field(None, description="Test coverage percentage")
    architecture_compliance: Dict[str, ModelSchemaValue] = Field(
        default_factory=dict, description="Architecture compliance"
    )


class IntelligenceDocumentContent(BaseModel):
    """Complete intelligence document content"""

    analysis_type: AnalysisType = Field(..., description="Type of analysis performed")
    metadata: IntelligenceMetadata = Field(..., description="Document metadata")
    change_summary: ChangeSummary = Field(..., description="Summary of changes")
    cross_repository_correlation: CrossRepositoryCorrelation = Field(
        ..., description="Correlation analysis"
    )
    security_and_privacy: SecurityAndPrivacy = Field(
        ..., description="Security analysis"
    )
    technical_analysis: Optional[TechnicalAnalysis] = Field(
        None, description="Technical analysis"
    )
    raw_diff: Optional[str] = Field(None, description="Raw git diff content")


# === MCP Request/Response Models ===


class MCPCreateDocumentRequest(BaseModel):
    """MCP request for creating intelligence documents"""

    method: str = Field("create_document", description="MCP method name")
    params: Dict[str, ModelSchemaValue] = Field(
        ..., description="MCP method parameters"
    )

    @classmethod
    def create_intelligence_document(
        cls,
        project_id: UUID,
        content: IntelligenceDocumentContent,
        repository_name: str,
    ) -> "MCPCreateDocumentRequest":
        """Create an MCP request for intelligence document"""
        return cls(
            method="create_document",
            params={
                "project_id": ModelSchemaValue.from_value(str(project_id)),
                "title": ModelSchemaValue.from_value(
                    f"Intelligence: {repository_name} Code Changes with Analysis"
                ),
                "document_type": ModelSchemaValue.from_value("intelligence"),
                "content": ModelSchemaValue.from_value(content.model_dump(mode="json")),
                "author": ModelSchemaValue.from_value("Intelligence Hook v3.1"),
                "tags": ModelSchemaValue.from_value(
                    [
                        "intelligence",
                        "automation",
                        "git-hook",
                        repository_name.lower(),
                    ]
                ),
            },
        )


class MCPResponse(BaseModel):
    """Standard MCP response"""

    success: bool = Field(..., description="Operation success status")
    document_id: Optional[UUID] = Field(None, description="Created document ID")
    message: Optional[str] = Field(None, description="Response message")
    error: Optional[str] = Field(None, description="Error message if failed")


# === Intelligence Service Request/Response Models ===


class IntelligenceServiceRequest(BaseModel):
    """Request for intelligence service document processing"""

    content: str = Field(..., description="Raw document content as JSON string")
    source_path: str = Field(..., description="Source path identifier")
    metadata: Dict[str, ModelSchemaValue] = Field(
        default_factory=dict, description="Additional metadata"
    )
    store_entities: bool = Field(
        True, description="Whether to store extracted entities"
    )
    extract_relationships: bool = Field(
        True, description="Whether to extract relationships"
    )
    trigger_freshness_analysis: bool = Field(
        True, description="Whether to trigger freshness analysis"
    )

    @classmethod
    def from_intelligence_document(
        cls,
        content: IntelligenceDocumentContent,
        repository_name: str,
        commit_hash: str,
    ) -> "IntelligenceServiceRequest":
        """Create intelligence service request from document content"""
        import json

        return cls(
            content=json.dumps(content.model_dump(mode="json"), indent=2),
            source_path=f"git://{repository_name}/commit/{commit_hash}",
            metadata={
                "type": ModelSchemaValue.from_value("intelligence_document"),
                "repository": ModelSchemaValue.from_value(repository_name),
                "commit_hash": ModelSchemaValue.from_value(commit_hash),
                "timestamp": ModelSchemaValue.from_value(
                    content.metadata.timestamp.isoformat()
                ),
                "generated_by": ModelSchemaValue.from_value("intelligence_hook_v3.1"),
            },
        )


class IntelligenceServiceResponse(BaseModel):
    """Response from intelligence service"""

    success: bool = Field(..., description="Processing success status")
    entities_extracted: int = Field(0, description="Number of entities extracted")
    relationships_found: int = Field(0, description="Number of relationships found")
    processing_time: float = Field(0.0, description="Processing time in seconds")
    error: Optional[str] = Field(None, description="Error message if failed")


# === Hook Configuration Models ===


class DiffAnalysisConfig(BaseModel):
    """Configuration for diff analysis"""

    enabled: bool = Field(True, description="Enable diff analysis")
    max_diff_size: int = Field(50000, description="Maximum diff size to process")
    context_lines: int = Field(3, description="Context lines in diff")
    filter_sensitive_content: bool = Field(
        True, description="Filter out sensitive content"
    )


class CorrelationAnalysisConfig(BaseModel):
    """Configuration for correlation analysis"""

    enabled: bool = Field(True, description="Enable correlation analysis")
    sibling_repositories: List[str] = Field(
        default_factory=list, description="Related repositories"
    )
    time_windows: List[int] = Field(
        default_factory=lambda: [6, 24, 72], description="Time windows in hours"
    )


class IntelligenceHookConfig(BaseModel):
    """Complete intelligence hook configuration"""

    intelligence_enabled: bool = Field(
        True, description="Enable intelligence processing"
    )
    archon_mcp_endpoint: str = Field(
        "http://localhost:8051/mcp", description="Archon MCP endpoint"
    )
    archon_project_id: UUID = Field(..., description="Target Archon project ID")
    diff_analysis: DiffAnalysisConfig = Field(
        default_factory=DiffAnalysisConfig, description="Diff analysis config"
    )
    correlation_analysis: CorrelationAnalysisConfig = Field(
        default_factory=CorrelationAnalysisConfig, description="Correlation config"
    )

    # Legacy support
    intelligence_api: Optional[Dict[str, ModelSchemaValue]] = Field(
        None, description="Legacy intelligence API config"
    )


# === Validation and Helper Functions ===


def validate_intelligence_document(
    content: Dict[str, object],
) -> IntelligenceDocumentContent:
    """Validate and parse intelligence document content"""
    return IntelligenceDocumentContent(**content)


def create_intelligence_metadata(
    repository: str,
    branch: str,
    commit: str,
    author: str,
    hook_version: ModelSemVer = parse_semver_from_string("3.1.0"),
) -> IntelligenceMetadata:
    """Create intelligence metadata with current timestamp"""
    return IntelligenceMetadata(
        timestamp=datetime.now(),
        repository=repository,
        branch=branch,
        commit=commit,
        author=author,
        hook_version=hook_version,
    )


def create_change_summary(
    commit_message: str,
    files_changed: int,
    lines_added: int = 0,
    lines_removed: int = 0,
    security_status: SecurityStatus = SecurityStatus.CLEAN,
) -> ChangeSummary:
    """Create change summary from git information"""
    return ChangeSummary(
        commit_message=commit_message,
        files_changed=files_changed,
        lines_added=lines_added,
        lines_removed=lines_removed,
        security_status=security_status,
    )
