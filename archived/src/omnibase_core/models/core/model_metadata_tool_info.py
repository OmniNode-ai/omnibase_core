"""
Metadata tool info model.
"""

from enum import Enum

from pydantic import BaseModel, Field

from .model_audit_entry import ModelAuditEntry
from .model_metadata_tool_usage_metrics import ModelMetadataToolUsageMetrics


class MetadataToolType(str, Enum):
    """Types of metadata tools."""

    FUNCTION = "function"
    DOCUMENTATION = "documentation"
    TEMPLATE = "template"
    GENERATOR = "generator"
    ANALYZER = "analyzer"
    VALIDATOR = "validator"
    FORMATTER = "formatter"


class MetadataToolStatus(str, Enum):
    """Status of metadata tools."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    LEGACY = "legacy"
    DISABLED = "disabled"


class MetadataToolComplexity(str, Enum):
    """Complexity levels for metadata tools."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ADVANCED = "advanced"


class ModelMetadataToolInfo(BaseModel):
    """Enhanced information about a metadata tool."""

    name: str = Field(..., description="Tool name")
    tool_type: MetadataToolType = Field(
        MetadataToolType.FUNCTION,
        description="Type of tool",
    )
    status: MetadataToolStatus = Field(
        MetadataToolStatus.ACTIVE,
        description="Tool status",
    )
    complexity: MetadataToolComplexity = Field(
        MetadataToolComplexity.SIMPLE,
        description="Tool complexity",
    )

    # Documentation and metadata
    description: str = Field("", description="Tool description")
    documentation: str = Field("", description="Detailed documentation")
    author: str = Field("Unknown", description="Tool author")
    version: str = Field("1.0.0", description="Tool version")
    tags: list[str] = Field(
        default_factory=list,
        description="Tool tags for categorization",
    )

    # Usage and performance
    usage_metrics: ModelMetadataToolUsageMetrics = Field(
        default_factory=ModelMetadataToolUsageMetrics,
        description="Usage metrics",
    )

    # Dependencies and relationships
    dependencies: list[str] = Field(
        default_factory=list,
        description="Tool dependencies",
    )
    related_tools: list[str] = Field(default_factory=list, description="Related tools")
    replaces: str | None = Field(
        None,
        description="Tool this replaces (for deprecation)",
    )

    # Security and compliance
    security_level: str = Field("standard", description="Security level required")
    compliance_notes: list[str] = Field(
        default_factory=list,
        description="Compliance notes",
    )
    audit_trail: list[ModelAuditEntry] = Field(
        default_factory=list,
        description="Audit trail",
    )
