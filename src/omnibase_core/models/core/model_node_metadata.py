"""
Node metadata model.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_schema import ModelSchema

from .model_audit_entry import ModelAuditEntry
from .model_node_performance_metrics import ModelNodePerformanceMetrics
from .model_node_validation_result import ModelNodeValidationResult


class NodeRegistrationStatus(str, Enum):
    """Status of node registration."""

    REGISTERED = "registered"
    PENDING = "pending"
    FAILED = "failed"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


class NodeCapabilityLevel(str, Enum):
    """Node capability levels."""

    BASIC = "basic"
    ADVANCED = "advanced"
    ENTERPRISE = "enterprise"
    EXPERIMENTAL = "experimental"


class NodeCategory(str, Enum):
    """Node categories for organization."""

    CORE = "core"
    REGISTRY = "registry"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    OUTPUT = "output"
    UTILITY = "utility"
    CUSTOM = "custom"


class NodeCompatibilityMode(str, Enum):
    """Node compatibility modes."""

    STRICT = "strict"
    COMPATIBLE = "compatible"
    LEGACY = "legacy"
    EXPERIMENTAL = "experimental"


class ModelNodeMetadata(BaseModel):
    """Comprehensive metadata for a registered node."""

    name: str = Field(..., description="Node name")
    node_class: str = Field(..., description="Node class name")
    module_path: str = Field(..., description="Node module path")
    registration_time: datetime = Field(
        default_factory=datetime.now,
        description="When node was registered",
    )
    status: NodeRegistrationStatus = Field(
        NodeRegistrationStatus.REGISTERED,
        description="Registration status",
    )
    category: NodeCategory = Field(NodeCategory.CUSTOM, description="Node category")
    capability_level: NodeCapabilityLevel = Field(
        NodeCapabilityLevel.BASIC,
        description="Capability level",
    )
    compatibility_mode: NodeCompatibilityMode = Field(
        NodeCompatibilityMode.COMPATIBLE,
        description="Compatibility mode",
    )

    # Performance and usage tracking
    performance_metrics: ModelNodePerformanceMetrics = Field(
        default_factory=ModelNodePerformanceMetrics,
        description="Performance metrics",
    )
    validation_result: ModelNodeValidationResult = Field(
        default_factory=ModelNodeValidationResult,
        description="Validation results",
    )

    # Documentation and configuration
    description: str = Field("", description="Node description")
    version: str = Field("1.0.0", description="Node version")
    author: str = Field("Unknown", description="Node author")
    documentation_url: str | None = Field(None, description="Documentation URL")
    configuration_schema: ModelSchema = Field(
        default_factory=dict,
        description="Configuration schema",
    )

    # Dependencies and requirements
    dependencies: list[str] = Field(
        default_factory=list,
        description="Node dependencies",
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
