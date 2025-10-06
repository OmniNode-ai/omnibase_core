from typing import Any

from pydantic import Field

from omnibase_core.enums.enum_metadata_tool_complexity import EnumMetadataToolComplexity
from omnibase_core.enums.enum_metadata_tool_status import EnumMetadataToolStatus
from omnibase_core.enums.enum_metadata_tool_type import EnumMetadataToolType

"""
Metadata tool info model.
"""

from enum import Enum

from pydantic import BaseModel, Field

from .model_audit_entry import ModelAuditEntry
from .model_metadata_tool_usage_metrics import ModelMetadataToolUsageMetrics
from .model_semver import ModelSemVer


class ModelMetadataToolInfo(BaseModel):
    """Enhanced information about a metadata tool."""

    name: str = Field(..., description="Tool name")
    tool_type: EnumMetadataToolType = Field(
        EnumMetadataToolType.FUNCTION,
        description="Type of tool",
    )
    status: EnumMetadataToolStatus = Field(
        EnumMetadataToolStatus.ACTIVE,
        description="Tool status",
    )
    complexity: EnumMetadataToolComplexity = Field(
        EnumMetadataToolComplexity.SIMPLE,
        description="Tool complexity",
    )

    # Documentation and metadata
    description: str = Field(default="", description="Tool description")
    documentation: str = Field(default="", description="Detailed documentation")
    author: str = Field("Unknown", description="Tool author")
    version: ModelSemVer = Field(
        default_factory=lambda: parse_semver_from_string("1.0.0"),
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
    security_level: str = Field("standard", description="Security level required")
    compliance_notes: list[str] = Field(
        default_factory=list,
        description="Compliance notes",
    )
    audit_trail: list[ModelAuditEntry] = Field(
        default_factory=list,
        description="Audit trail",
    )
