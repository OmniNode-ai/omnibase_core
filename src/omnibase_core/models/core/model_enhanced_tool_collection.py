from pydantic import Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

"""
Enhanced tool collection models.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.
"""

import hashlib
import inspect
from collections.abc import ItemsView, KeysView, ValuesView
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from pydantic import BaseModel, ValidationInfo, computed_field

from omnibase_core.models.core.model_performance_summary import ModelPerformanceSummary
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import (
    TypedDictAccessControlConfig,
    TypedDictSecurityPolicyConfig,
)

from .model_tool_metadata import (
    EnumToolCapabilityLevel,
    EnumToolCategory,
    EnumToolCompatibilityMode,
    EnumToolRegistrationStatus,
    ModelToolMetadata,
)

# Import separated models
from .model_tool_performance_metrics import ModelToolPerformanceMetrics
from .model_tool_validation_result import ModelToolValidationResult

# Removed circular import to avoid issues


class ModelToolCollection(BaseModel):
    """
    Enterprise-grade collection of executable tools for ONEX registries.

    Enhanced with comprehensive tool management, performance monitoring,
    validation capabilities, and operational insights for production deployment.
    """

    # Core tool storage (enhanced)
    # ONEX_EXCLUDE: dict_str_object - Heterogeneous tool registry (classes, configs, instances)
    tools: dict[str, object] = Field(
        default_factory=dict,
        description="Mapping of tool names to ProtocolTool implementations",
    )

    # Enterprise enhancements
    tool_metadata: dict[str, ModelToolMetadata] = Field(
        default_factory=dict,
        description="Comprehensive metadata for each registered tool",
    )

    # Collection management
    collection_id: UUID = Field(default=..., description="Unique collection identifier")
    collection_name: str = Field(
        default="default",
        description="Human-readable collection name",
    )
    collection_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Collection version",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Collection creation time",
    )
    last_modified: datetime = Field(
        default_factory=datetime.now,
        description="Last modification time",
    )

    # Operational configuration
    max_tools: int = Field(default=100, description="Maximum number of tools allowed")
    auto_validation: bool = Field(
        default=True,
        description="Whether to automatically validate tools",
    )
    performance_monitoring: bool = Field(
        default=True,
        description="Whether to track performance metrics",
    )
    strict_mode: bool = Field(
        default=False, description="Whether to enforce strict validation"
    )

    # Analytics and insights
    total_registrations: int = Field(
        default=0,
        description="Total number of tool registrations",
    )
    active_tool_count: int = Field(default=0, description="Number of active tools")
    deprecated_tool_count: int = Field(
        default=0, description="Number of deprecated tools"
    )
    failed_registration_count: int = Field(
        default=0,
        description="Number of failed registrations",
    )

    # Security and compliance
    security_policy: TypedDictSecurityPolicyConfig = Field(
        default_factory=lambda: cast(TypedDictSecurityPolicyConfig, {}),
        description="Security policy configuration",
    )
    compliance_requirements: list[str] = Field(
        default_factory=list,
        description="Compliance requirements",
    )
    access_control: TypedDictAccessControlConfig = Field(
        default_factory=lambda: cast(TypedDictAccessControlConfig, {}),
        description="Access control settings",
    )

    def __init__(self, **data: object) -> None:
        # Generate collection_id if not provided
        if "collection_id" not in data:
            timestamp = datetime.now().isoformat()
            content = f"tool_collection_{timestamp}"
            data["collection_id"] = hashlib.sha256(content.encode()).hexdigest()[:16]
        super().__init__(**data)

    @computed_field
    def collection_hash(self) -> str:
        """Generate unique hash for this collection state."""
        tool_names = sorted(self.tools.keys())
        content = f"{self.collection_id}:{':'.join(tool_names)}:{self.last_modified.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @computed_field
    def tool_count_by_category(self) -> dict[str, int]:
        """Count tools by category."""
        counts: dict[str, int] = {}
        for metadata in self.tool_metadata.values():
            category = metadata.category.value
            counts[category] = counts.get(category, 0) + 1
        return counts

    @computed_field
    def tool_count_by_status(self) -> dict[str, int]:
        """Count tools by registration status."""
        counts: dict[str, int] = {}
        for metadata in self.tool_metadata.values():
            status = metadata.status.value
            counts[status] = counts.get(status, 0) + 1
        return counts

    @computed_field
    def collection_health_score(self) -> float:
        """Calculate overall collection health score (0-100)."""
        if not self.tool_metadata:
            return 100.0

        total_score = 0.0
        for metadata in self.tool_metadata.values():
            tool_score = 0.0

            # Validation score (40%)
            if metadata.validation_result.is_valid:
                tool_score += 40.0

            # Performance score (30%)
            if metadata.performance_metrics.success_rate_percent >= 95:
                tool_score += 30.0
            elif metadata.performance_metrics.success_rate_percent >= 80:
                tool_score += 20.0
            elif metadata.performance_metrics.success_rate_percent >= 50:
                tool_score += 10.0

            # Status score (20%)
            if metadata.status == EnumToolRegistrationStatus.REGISTERED:
                tool_score += 20.0
            elif metadata.status == EnumToolRegistrationStatus.DEPRECATED:
                tool_score += 10.0

            # Dependencies score (10%)
            if metadata.validation_result.dependencies_satisfied:
                tool_score += 10.0

            total_score += tool_score

        return total_score / len(self.tool_metadata)

    @field_validator("max_tools")
    @classmethod
    def validate_max_tools(cls, v: int, info: ValidationInfo) -> int:
        """Validate maximum tools limit."""
        if v < 1 or v > 1000:
            msg = "max_tools must be between 1 and 1000"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    def register_tool(
        self, name: str, tool_class: type[object], **metadata_kwargs: Any
    ) -> bool:
        """Register a tool implementation with comprehensive validation and metadata."""
        try:
            # Check collection limits
            if len(self.tools) >= self.max_tools:
                return False

            # Validate tool implementation
            validation_result = self._validate_tool(tool_class)

            if self.strict_mode and not validation_result.is_valid:
                return False

            # Register the tool
            self.tools[name] = tool_class

            # Create comprehensive metadata
            metadata = ModelToolMetadata(
                name=name,
                tool_class=tool_class.__name__,
                module_path=tool_class.__module__,
                validation_result=validation_result,
                **metadata_kwargs,
            )

            # Auto-detect category from class or module name
            if metadata.category == EnumToolCategory.CUSTOM:
                metadata.category = self._detect_tool_category(tool_class)

            self.tool_metadata[name] = metadata

            # Update collection statistics
            self.total_registrations += 1
            self.active_tool_count = len(
                [
                    m
                    for m in self.tool_metadata.values()
                    if m.status == EnumToolRegistrationStatus.REGISTERED
                ],
            )
            self.last_modified = datetime.now()

            return True

        except Exception:  # fallback-ok: registration method, False indicates failure with metrics update
            self.failed_registration_count += 1
            return False

    def _validate_tool(self, tool_class: type[object]) -> ModelToolValidationResult:
        """Validate tool implementation against ProtocolTool interface."""
        result = ModelToolValidationResult()

        try:
            # Check if it's a class
            if not inspect.isclass(tool_class):
                result.is_valid = False
                result.validation_errors.append("Tool must be a class")
                return result

            # Check ProtocolTool inheritance/compliance
            if not hasattr(tool_class, "__annotations__"):
                result.interface_compliance = False
                result.validation_warnings.append("Tool class lacks type annotations")

            # Check for required methods (basic ProtocolTool interface)
            required_methods = ["execute", "__init__"]
            for method_name in required_methods:
                if not hasattr(tool_class, method_name):
                    result.is_valid = False
                    result.validation_errors.append(
                        f"Missing required method: {method_name}",
                    )

            # Validate method signatures
            if hasattr(tool_class, "execute"):
                sig = inspect.signature(tool_class.execute)
                if len(sig.parameters) < 1:  # Should have self at minimum
                    result.signature_valid = False
                    result.validation_warnings.append(
                        "execute method signature may be invalid",
                    )

            # Check for common issues
            if tool_class.__name__.startswith("_"):
                result.validation_warnings.append(
                    "Tool class name starts with underscore (private)",
                )

        except (AttributeError, TypeError, ValueError) as e:
            result.is_valid = False
            result.validation_errors.append(f"Validation failed: {e!s}")

        return result

    def _detect_tool_category(self, tool_class: type[object]) -> EnumToolCategory:
        """Auto-detect tool category from class or module name."""
        class_name = tool_class.__name__.lower()
        module_name = tool_class.__module__.lower()

        # Category detection based on naming patterns
        if "registry" in class_name or "registry" in module_name:
            return EnumToolCategory.REGISTRY
        if "validate" in class_name or "validator" in class_name:
            return EnumToolCategory.VALIDATION
        if "transform" in class_name or "convert" in class_name:
            return EnumToolCategory.TRANSFORMATION
        if "output" in class_name or "format" in class_name:
            return EnumToolCategory.OUTPUT
        if "core" in module_name or "essential" in class_name:
            return EnumToolCategory.CORE
        if "util" in class_name or "helper" in class_name:
            return EnumToolCategory.UTILITY
        return EnumToolCategory.CUSTOM

    def get_tool(self, name: str) -> object | None:
        """Get a tool implementation by name."""
        return self.tools.get(name)

    def get_performance_summary(self) -> ModelPerformanceSummary:
        """Get comprehensive performance summary for all tools."""
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        if not self.tool_metadata:
            return ModelPerformanceSummary(
                total_execution_time_ms=0.0,
                measurement_start=now,
                measurement_end=now,
                measurement_duration_seconds=0.0,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
            )

        total_executions = sum(
            m.performance_metrics.total_executions for m in self.tool_metadata.values()
        )
        avg_success_rate = sum(
            m.performance_metrics.success_rate_percent
            for m in self.tool_metadata.values()
        ) / len(self.tool_metadata)
        avg_execution_time = sum(
            m.performance_metrics.avg_execution_time_ms
            for m in self.tool_metadata.values()
        ) / len(self.tool_metadata)
        total_exec_time = sum(
            m.performance_metrics.avg_execution_time_ms
            * m.performance_metrics.total_executions
            for m in self.tool_metadata.values()
        )

        successful = int(total_executions * avg_success_rate / 100)

        return ModelPerformanceSummary(
            total_execution_time_ms=total_exec_time,
            average_response_time_ms=avg_execution_time,
            measurement_start=now,
            measurement_end=now,
            measurement_duration_seconds=0.0,
            total_requests=int(total_executions),
            successful_requests=successful,
            failed_requests=int(total_executions) - successful,
        )

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self.tools

    def __contains__(self, name: str) -> bool:
        """Support 'in' operator."""
        return self.has_tool(name)

    def __getitem__(self, name: str) -> object:
        """Support dict-like access."""
        tool = self.get_tool(name)
        if tool is None:
            msg = f"Tool '{name}' not found in collection"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.ITEM_NOT_REGISTERED,
                message=msg,
            )
        return tool

    def __setitem__(self, name: str, tool_class: type[object]) -> None:
        """Support dict-like assignment."""
        self.register_tool(name, tool_class)

    def keys(self) -> KeysView[str]:
        """Support dict-like keys() method."""
        return self.tools.keys()

    def values(self) -> ValuesView[object]:
        """Support dict-like values() method."""
        return self.tools.values()

    def items(self) -> ItemsView[str, object]:
        """Support dict-like items() method."""
        return self.tools.items()

    # Factory methods for common scenarios
    @classmethod
    def create_empty_collection(
        cls,
        name: str = "default",
        strict_mode: bool = False,
        max_tools: int = 100,
    ) -> "ModelToolCollection":
        """Create an empty tool collection with specified configuration."""
        return cls(collection_name=name, strict_mode=strict_mode, max_tools=max_tools)

    @classmethod
    def create_from_tools_dict(
        cls,
        # ONEX_EXCLUDE: dict_str_object - Heterogeneous tool registry (classes, configs, instances)
        tools_dict: dict[str, type[object]],
        collection_name: str = "imported",
        auto_validate: bool = True,
    ) -> "ModelToolCollection":
        """Create collection from existing tools dictionary."""
        collection = cls(collection_name=collection_name, auto_validation=auto_validate)

        for name, tool_class in tools_dict.items():
            collection.register_tool(name, tool_class)

        return collection

    @classmethod
    def create_production_collection(
        cls,
        name: str,
        max_tools: int = 50,
    ) -> "ModelToolCollection":
        """Create a production-ready collection with strict validation."""
        return cls(
            collection_name=name,
            strict_mode=True,
            auto_validation=True,
            performance_monitoring=True,
            max_tools=max_tools,
        )


# Compatibility aliases
ToolPerformanceMetrics = ModelToolPerformanceMetrics
ToolValidationResult = ModelToolValidationResult
ToolMetadata = ModelToolMetadata
ToolCollection = ModelToolCollection
ToolCapabilityLevel = EnumToolCapabilityLevel
ToolCategory = EnumToolCategory
ToolCompatibilityMode = EnumToolCompatibilityMode
ToolRegistrationStatus = EnumToolRegistrationStatus

# Re-export for current standards
__all__ = [
    "EnumToolCapabilityLevel",
    "EnumToolCategory",
    "EnumToolCompatibilityMode",
    "EnumToolRegistrationStatus",
    "ModelToolCollection",
    "ModelToolMetadata",
    "ModelToolPerformanceMetrics",
    "ModelToolValidationResult",
    "ToolMetadata",
    "ToolPerformanceMetrics",
    "ToolValidationResult",
]
