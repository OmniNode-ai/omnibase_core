"""
Metadata tool info model.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_metadata_tool_complexity import EnumMetadataToolComplexity
from omnibase_core.enums.enum_metadata_tool_status import EnumMetadataToolStatus
from omnibase_core.enums.enum_metadata_tool_type import EnumMetadataToolType
from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_audit_entry import ModelAuditEntry
from .model_metadata_tool_usage_metrics import ModelMetadataToolUsageMetrics


class ModelMetadataToolInfo(BaseModel):
    """Enhanced information about a metadata tool."""

    name: str = Field(default=..., description="Tool name")
    tool_type: EnumMetadataToolType = Field(
        default=EnumMetadataToolType.FUNCTION,
        description="Type of tool",
    )
    status: EnumMetadataToolStatus = Field(
        default=EnumMetadataToolStatus.ACTIVE,
        description="Tool status",
    )
    complexity: EnumMetadataToolComplexity = Field(
        default=EnumMetadataToolComplexity.SIMPLE,
        description="Tool complexity",
    )

    # Documentation and metadata
    description: str = Field(default="", description="Tool description")
    documentation: str = Field(default="", description="Detailed documentation")
    author: str = Field(default="Unknown", description="Tool author")
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Tool version",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tool tags for categorization",
    )

    # Usage and performance
    usage_metrics: ModelMetadataToolUsageMetrics = Field(
        default_factory=lambda: ModelMetadataToolUsageMetrics(),
        description="Usage metrics",
    )

    # Dependencies and relationships
    dependencies: list[str] = Field(
        default_factory=list,
        description="Tool dependencies",
    )
    related_tools: list[str] = Field(default_factory=list, description="Related tools")
    replaces: str | None = Field(
        default=None,
        description="Tool this replaces (for deprecation)",
    )

    # Security and compliance
    security_level: str = Field(
        default="standard", description="Security level required"
    )
    compliance_notes: list[str] = Field(
        default_factory=list,
        description="Compliance notes",
    )
    audit_trail: list[ModelAuditEntry] = Field(
        default_factory=list,
        description="Audit trail",
    )
