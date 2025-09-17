"""
Metadata node info model.
"""

from enum import Enum

from pydantic import BaseModel, Field

from .model_audit_entry import ModelAuditEntry
from .model_metadata_node_usage_metrics import ModelMetadataNodeUsageMetrics


class ModelMetadataNodeType(str, Enum):
    """Types of metadata nodes."""

    FUNCTION = "function"
    DOCUMENTATION = "documentation"
    TEMPLATE = "template"
    GENERATOR = "generator"
    ANALYZER = "analyzer"
    VALIDATOR = "validator"
    FORMATTER = "formatter"


class ModelMetadataNodeStatus(str, Enum):
    """Status of metadata nodes."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    LEGACY = "legacy"
    DISABLED = "disabled"


class ModelMetadataNodeComplexity(str, Enum):
    """Complexity levels for metadata nodes."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ADVANCED = "advanced"


class ModelMetadataNodeInfo(BaseModel):
    """Enhanced information about a metadata node."""

    name: str = Field(..., description="Node name")
    node_type: ModelMetadataNodeType = Field(
        ModelMetadataNodeType.FUNCTION,
        description="Type of node",
    )
    status: ModelMetadataNodeStatus = Field(
        ModelMetadataNodeStatus.ACTIVE,
        description="Node status",
    )
    complexity: ModelMetadataNodeComplexity = Field(
        ModelMetadataNodeComplexity.SIMPLE,
        description="Node complexity",
    )

    # Documentation and metadata
    description: str = Field("", description="Node description")
    documentation: str = Field("", description="Detailed documentation")
    author: str = Field("Unknown", description="Node author")
    version: str = Field("1.0.0", description="Node version")
    tags: list[str] = Field(
        default_factory=list,
        description="Node tags for categorization",
    )

    # Usage and performance
    usage_metrics: ModelMetadataNodeUsageMetrics = Field(
        default_factory=ModelMetadataNodeUsageMetrics,
        description="Usage metrics",
    )

    # Dependencies and relationships
    dependencies: list[str] = Field(
        default_factory=list,
        description="Node dependencies",
    )
    related_nodes: list[str] = Field(default_factory=list, description="Related nodes")
    replaces: str | None = Field(
        None,
        description="Node this replaces (for deprecation)",
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
