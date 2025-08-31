"""
Enhanced tool collection models.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.
"""

import hashlib
import inspect
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field, field_validator

from omnibase_core.model.core.model_performance_summary import ModelPerformanceSummary

from .model_tool_metadata import (
    ModelToolMetadata,
    ToolCapabilityLevel,
    ToolCategory,
    ToolCompatibilityMode,
    ToolRegistrationStatus,
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
    tools: dict[str, Any] = Field(
        default_factory=dict,
        description="Mapping of tool names to ProtocolTool implementations",
    )

    # Enterprise enhancements
    tool_metadata: dict[str, ModelToolMetadata] = Field(
        default_factory=dict,
        description="Comprehensive metadata for each registered tool",
    )

    # Collection management
    collection_id: str = Field(..., description="Unique collection identifier")
    collection_name: str = Field(
        "default",
        description="Human-readable collection name",
    )
    collection_version: str = Field("1.0.0", description="Collection version")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Collection creation time",
    )
    last_modified: datetime = Field(
        default_factory=datetime.now,
        description="Last modification time",
    )

    # Operational configuration
    max_tools: int = Field(100, description="Maximum number of tools allowed")
    auto_validation: bool = Field(
        True,
        description="Whether to automatically validate tools",
    )
    performance_monitoring: bool = Field(
        True,
        description="Whether to track performance metrics",
    )
    strict_mode: bool = Field(False, description="Whether to enforce strict validation")

    # Analytics and insights
    total_registrations: int = Field(
        0,
        description="Total number of tool registrations",
    )
    active_tool_count: int = Field(0, description="Number of active tools")
    deprecated_tool_count: int = Field(0, description="Number of deprecated tools")
    failed_registration_count: int = Field(
        0,
        description="Number of failed registrations",
    )

    # Security and compliance
    security_policy: dict[str, Any] = Field(
        default_factory=dict,
        description="Security policy configuration",
    )
    compliance_requirements: list[str] = Field(
        default_factory=list,
        description="Compliance requirements",
    )
    access_control: dict[str, Any] = Field(
        default_factory=dict,
        description="Access control settings",
    )

    def __init__(self, **data):
        # Generate collection_id if not provided
        if "collection_id" not in data:
            timestamp = datetime.now().isoformat()
            content = f"tool_collection_{timestamp}"
            data["collection_id"] = hashlib.sha256(content.encode()).hexdigest()[:16]
        super().__init__(**data)

    @computed_field
    @property
    def collection_hash(self) -> str:
        """Generate unique hash for this collection state."""
        tool_names = sorted(self.tools.keys())
        content = f"{self.collection_id}:{':'.join(tool_names)}:{self.last_modified.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @computed_field
    @property
    def tool_count_by_category(self) -> dict[str, int]:
        """Count tools by category."""
        counts = {}
        for metadata in self.tool_metadata.values():
            category = metadata.category.value
            counts[category] = counts.get(category, 0) + 1
        return counts

    @computed_field
    @property
    def tool_count_by_status(self) -> dict[str, int]:
        """Count tools by registration status."""
        counts = {}
        for metadata in self.tool_metadata.values():
            status = metadata.status.value
            counts[status] = counts.get(status, 0) + 1
        return counts

    @computed_field
    @property
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
            if metadata.status == ToolRegistrationStatus.REGISTERED:
                tool_score += 20.0
            elif metadata.status == ToolRegistrationStatus.DEPRECATED:
                tool_score += 10.0

            # Dependencies score (10%)
            if metadata.validation_result.dependencies_satisfied:
                tool_score += 10.0

            total_score += tool_score

        return total_score / len(self.tool_metadata)

    @field_validator("max_tools")
    def validate_max_tools(self, v, info):
        """Validate maximum tools limit."""
        if v < 1 or v > 1000:
            msg = "max_tools must be between 1 and 1000"
            raise ValueError(msg)
        return v

    def register_tool(self, name: str, tool_class: Any, **metadata_kwargs) -> bool:
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
            if metadata.category == ToolCategory.CUSTOM:
                metadata.category = self._detect_tool_category(tool_class)

            self.tool_metadata[name] = metadata

            # Update collection statistics
            self.total_registrations += 1
            self.active_tool_count = len(
                [
                    m
                    for m in self.tool_metadata.values()
                    if m.status == ToolRegistrationStatus.REGISTERED
                ],
            )
            self.last_modified = datetime.now()

            return True

        except Exception:
            self.failed_registration_count += 1
            return False

    def _validate_tool(self, tool_class: Any) -> ModelToolValidationResult:
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

        except Exception as e:
            result.is_valid = False
            result.validation_errors.append(f"Validation failed: {e!s}")

        return result

    def _detect_tool_category(self, tool_class: Any) -> ToolCategory:
        """Auto-detect tool category from class or module name."""
        class_name = tool_class.__name__.lower()
        module_name = tool_class.__module__.lower()

        # Category detection based on naming patterns
        if "registry" in class_name or "registry" in module_name:
            return ToolCategory.REGISTRY
        if "validate" in class_name or "validator" in class_name:
            return ToolCategory.VALIDATION
        if "transform" in class_name or "convert" in class_name:
            return ToolCategory.TRANSFORMATION
        if "output" in class_name or "format" in class_name:
            return ToolCategory.OUTPUT
        if "core" in module_name or "essential" in class_name:
            return ToolCategory.CORE
        if "util" in class_name or "helper" in class_name:
            return ToolCategory.UTILITY
        return ToolCategory.CUSTOM

    def get_tool(self, name: str) -> Any | None:
        """Get a tool implementation by name."""
        return self.tools.get(name)

    def get_performance_summary(self) -> ModelPerformanceSummary:
        """Get comprehensive performance summary for all tools."""
        if not self.tool_metadata:
            return ModelPerformanceSummary(total_tools=0, summary="No tools registered")

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

        return ModelPerformanceSummary(
            total_tools=len(self.tools),
            active_tools=self.active_tool_count,
            deprecated_tools=self.deprecated_tool_count,
            total_executions=total_executions,
            avg_success_rate_percent=avg_success_rate,
            avg_execution_time_ms=avg_execution_time,
            collection_health_score=self.collection_health_score,
            tools_by_category=self.tool_count_by_category,
            tools_by_status=self.tool_count_by_status,
        )

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self.tools

    def __contains__(self, name: str) -> bool:
        """Support 'in' operator."""
        return self.has_tool(name)

    def __getitem__(self, name: str) -> Any:
        """Support dict-like access."""
        tool = self.get_tool(name)
        if tool is None:
            msg = f"Tool '{name}' not found in collection"
            raise KeyError(msg)
        return tool

    def __setitem__(self, name: str, tool_class: Any) -> None:
        """Support dict-like assignment."""
        self.register_tool(name, tool_class)

    def keys(self):
        """Support dict-like keys() method."""
        return self.tools.keys()

    def values(self):
        """Support dict-like values() method."""
        return self.tools.values()

    def items(self):
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
        tools_dict: dict[str, Any],
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


# Backward compatibility aliases
ToolPerformanceMetrics = ModelToolPerformanceMetrics
ToolValidationResult = ModelToolValidationResult
ToolMetadata = ModelToolMetadata
ToolCollection = ModelToolCollection

# Re-export for backward compatibility
__all__ = [
    "ModelToolCollection",
    "ModelToolMetadata",
    "ModelToolPerformanceMetrics",
    "ModelToolValidationResult",
    "ToolCapabilityLevel",
    "ToolCategory",
    "ToolCollection",
    "ToolCompatibilityMode",
    "ToolMetadata",
    # Backward compatibility
    "ToolPerformanceMetrics",
    "ToolRegistrationStatus",
    "ToolValidationResult",
]
