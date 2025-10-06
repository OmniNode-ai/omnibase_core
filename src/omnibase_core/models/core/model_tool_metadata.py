from typing import Any, Optional

from pydantic import Field

from omnibase_core.enums.enum_tool_capability_level import EnumToolCapabilityLevel
from omnibase_core.enums.enum_tool_category import EnumToolCategory
from omnibase_core.enums.enum_tool_compatibility_mode import EnumToolCompatibilityMode
from omnibase_core.enums.enum_tool_registration_status import EnumToolRegistrationStatus
from omnibase_core.models.core.model_semver import ModelSemVer

"""
Tool metadata model.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_schema import ModelSchema

from .model_audit_entry import ModelAuditEntry
from .model_tool_performance_metrics import ModelToolPerformanceMetrics
from .model_tool_validation_result import ModelToolValidationResult


class ModelToolMetadata(BaseModel):
    """Comprehensive metadata for a registered tool."""

    name: str = Field(default=..., description="Tool name")
    tool_class: str = Field(default=..., description="Tool class name")
    module_path: str = Field(default=..., description="Tool module path")
    registration_time: datetime = Field(
        default_factory=datetime.now,
        description="When tool was registered",
    )
    status: EnumToolRegistrationStatus = Field(
        default=EnumToolRegistrationStatus.REGISTERED,
        description="Registration status",
    )
    category: EnumToolCategory = Field(
        default=EnumToolCategory.CUSTOM, description="Tool category"
    )
    capability_level: EnumToolCapabilityLevel = Field(
        default=EnumToolCapabilityLevel.BASIC,
        description="Capability level",
    )
    compatibility_mode: EnumToolCompatibilityMode = Field(
        default=EnumToolCompatibilityMode.COMPATIBLE,
        description="Compatibility mode",
    )

    # Performance and usage tracking
    performance_metrics: ModelToolPerformanceMetrics = Field(
        default_factory=lambda: ModelToolPerformanceMetrics(),
        description="Performance metrics",
    )
    validation_result: ModelToolValidationResult = Field(
        default_factory=lambda: ModelToolValidationResult(),
        description="Validation results",
    )

    # Documentation and configuration
    description: str = Field(default="", description="Tool description")
    version: ModelSemVer = Field(default="1.0.0", description="Tool version")
    author: str = Field(default="Unknown", description="Tool author")
    documentation_url: str | None = Field(default=None, description="Documentation URL")
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
    security_level: str = Field(
        default="standard", description="Security clearance level"
    )
    compliance_tags: list[str] = Field(
        default_factory=list,
        description="Compliance tags",
    )
    audit_trail: list[ModelAuditEntry] = Field(
        default_factory=list,
        description="Audit trail entries",
    )
