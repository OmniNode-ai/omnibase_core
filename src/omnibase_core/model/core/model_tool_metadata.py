"""
Tool metadata model.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_schema import ModelSchema

from .model_audit_entry import ModelAuditEntry
from .model_tool_performance_metrics import ModelToolPerformanceMetrics
from .model_tool_validation_result import ModelToolValidationResult


class ToolRegistrationStatus(str, Enum):
    """Status of tool registration."""

    REGISTERED = "registered"
    PENDING = "pending"
    FAILED = "failed"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


class ToolCapabilityLevel(str, Enum):
    """Tool capability levels."""

    BASIC = "basic"
    ADVANCED = "advanced"
    ENTERPRISE = "enterprise"
    EXPERIMENTAL = "experimental"


class ToolCategory(str, Enum):
    """Tool categories for organization."""

    CORE = "core"
    REGISTRY = "registry"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    OUTPUT = "output"
    UTILITY = "utility"
    CUSTOM = "custom"


class ToolCompatibilityMode(str, Enum):
    """Tool compatibility modes."""

    STRICT = "strict"
    COMPATIBLE = "compatible"
    LEGACY = "legacy"
    EXPERIMENTAL = "experimental"


class ModelToolMetadata(BaseModel):
    """Comprehensive metadata for a registered tool."""

    name: str = Field(..., description="Tool name")
    tool_class: str = Field(..., description="Tool class name")
    module_path: str = Field(..., description="Tool module path")
    registration_time: datetime = Field(
        default_factory=datetime.now,
        description="When tool was registered",
    )
    status: ToolRegistrationStatus = Field(
        ToolRegistrationStatus.REGISTERED,
        description="Registration status",
    )
    category: ToolCategory = Field(ToolCategory.CUSTOM, description="Tool category")
    capability_level: ToolCapabilityLevel = Field(
        ToolCapabilityLevel.BASIC,
        description="Capability level",
    )
    compatibility_mode: ToolCompatibilityMode = Field(
        ToolCompatibilityMode.COMPATIBLE,
        description="Compatibility mode",
    )

    # Performance and usage tracking
    performance_metrics: ModelToolPerformanceMetrics = Field(
        default_factory=ModelToolPerformanceMetrics,
        description="Performance metrics",
    )
    validation_result: ModelToolValidationResult = Field(
        default_factory=ModelToolValidationResult,
        description="Validation results",
    )

    # Documentation and configuration
    description: str = Field("", description="Tool description")
    version: str = Field("1.0.0", description="Tool version")
    author: str = Field("Unknown", description="Tool author")
    documentation_url: str | None = Field(None, description="Documentation URL")
    configuration_schema: ModelSchema = Field(
        default_factory=dict,
        description="Configuration schema",
    )

    # Dependencies and requirements
    dependencies: list[str] = Field(
        default_factory=list,
        description="Tool dependencies",
    )
    required_protocols: list[str] = Field(
        default_factory=list,
        description="Required protocol interfaces",
    )
    optional_protocols: list[str] = Field(
        default_factory=list,
        description="Optional protocol interfaces",
    )

    # Security and compliance
    security_level: str = Field("standard", description="Security clearance level")
    compliance_tags: list[str] = Field(
        default_factory=list,
        description="Compliance tags",
    )
    audit_trail: list[ModelAuditEntry] = Field(
        default_factory=list,
        description="Audit trail entries",
    )
