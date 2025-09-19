"""
Metadata node info model.

Enhanced information about a metadata node with strongly typed enums.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.nodes.enum_metadata_node_complexity import (
    EnumMetadataNodeComplexity,
)
from omnibase_core.enums.nodes.enum_metadata_node_status import EnumMetadataNodeStatus
from omnibase_core.enums.nodes.enum_metadata_node_type import EnumMetadataNodeType
from omnibase_core.enums.nodes.enum_security_level import EnumSecurityLevel
from omnibase_core.models.core.model_audit_entry import ModelAuditEntry

from .model_metadata_node_usage_metrics import ModelMetadataNodeUsageMetrics


class ModelMetadataNodeInfo(BaseModel):
    """Enhanced information about a metadata node."""

    name: str = Field(..., description="Node name")
    node_type: EnumMetadataNodeType = Field(
        EnumMetadataNodeType.FUNCTION,
        description="Type of node",
    )
    status: EnumMetadataNodeStatus = Field(
        EnumMetadataNodeStatus.ACTIVE,
        description="Node status",
    )
    complexity: EnumMetadataNodeComplexity = Field(
        EnumMetadataNodeComplexity.SIMPLE,
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
        default_factory=lambda: ModelMetadataNodeUsageMetrics(
            total_invocations=0,
            success_count=0,
            failure_count=0,
            avg_processing_time_ms=0.0,
            last_used=None,
            most_recent_error=None,
            popularity_score=0.0,
        ),
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

    # Security and compliance with strongly typed enum
    security_level: EnumSecurityLevel = Field(
        EnumSecurityLevel.STANDARD, description="Security level required"
    )
    compliance_notes: list[str] = Field(
        default_factory=list,
        description="Compliance notes",
    )
    audit_trail: list[ModelAuditEntry] = Field(
        default_factory=list,
        description="Audit trail",
    )
