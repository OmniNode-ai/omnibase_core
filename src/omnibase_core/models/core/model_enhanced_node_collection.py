"""
Enhanced node collection models.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.
"""

import hashlib
import inspect
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field, field_validator

from omnibase_core.models.core.model_performance_summary import ModelPerformanceSummary

from .model_node_metadata import (
    ModelNodeMetadata,
    NodeCapabilityLevel,
    NodeCategory,
    NodeCompatibilityMode,
    NodeRegistrationStatus,
)

# Import separated models
from .model_node_performance_metrics import ModelNodePerformanceMetrics
from .model_node_validation_result import ModelNodeValidationResult

# Removed circular import to avoid issues


class ModelNodeCollection(BaseModel):
    """
    Enterprise-grade collection of executable nodes for ONEX registries.

    Enhanced with comprehensive node management, performance monitoring,
    validation capabilities, and operational insights for production deployment.
    """

    # Core node storage (enhanced)
    nodes: dict[str, Any] = Field(
        default_factory=dict,
        description="Mapping of node names to ProtocolNode implementations",
    )

    # Enterprise enhancements
    node_metadata: dict[str, ModelNodeMetadata] = Field(
        default_factory=dict,
        description="Comprehensive metadata for each registered node",
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
    max_nodes: int = Field(100, description="Maximum number of nodes allowed")
    auto_validation: bool = Field(
        True,
        description="Whether to automatically validate nodes",
    )
    performance_monitoring: bool = Field(
        True,
        description="Whether to track performance metrics",
    )
    strict_mode: bool = Field(False, description="Whether to enforce strict validation")

    # Analytics and insights
    total_registrations: int = Field(
        0,
        description="Total number of node registrations",
    )
    active_node_count: int = Field(0, description="Number of active nodes")
    deprecated_node_count: int = Field(0, description="Number of deprecated nodes")
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
            content = f"node_collection_{timestamp}"
            data["collection_id"] = hashlib.sha256(content.encode()).hexdigest()[:16]
        super().__init__(**data)

    @computed_field
    def collection_hash(self) -> str:
        """Generate unique hash for this collection state."""
        node_names = sorted(self.nodes.keys())
        content = f"{self.collection_id}:{':'.join(node_names)}:{self.last_modified.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @computed_field
    def node_count_by_category(self) -> dict[str, int]:
        """Count nodes by category."""
        counts: dict[str, int] = {}
        for metadata in self.node_metadata.values():
            category = metadata.category.value
            counts[category] = counts.get(category, 0) + 1
        return counts

    @computed_field
    def node_count_by_status(self) -> dict[str, int]:
        """Count nodes by registration status."""
        counts: dict[str, int] = {}
        for metadata in self.node_metadata.values():
            status = metadata.status.value
            counts[status] = counts.get(status, 0) + 1
        return counts

    @computed_field
    def collection_health_score(self) -> float:
        """Calculate overall collection health score (0-100)."""
        if not self.node_metadata:
            return 100.0

        total_score = 0.0
        for metadata in self.node_metadata.values():
            node_score = 0.0

            # Validation score (40%)
            if metadata.validation_result.is_valid:
                node_score += 40.0

            # Performance score (30%)
            if metadata.performance_metrics.success_rate_percent >= 95:
                node_score += 30.0
            elif metadata.performance_metrics.success_rate_percent >= 80:
                node_score += 20.0
            elif metadata.performance_metrics.success_rate_percent >= 50:
                node_score += 10.0

            # Status score (20%)
            if metadata.status == NodeRegistrationStatus.REGISTERED:
                node_score += 20.0
            elif metadata.status == NodeRegistrationStatus.DEPRECATED:
                node_score += 10.0

            # Dependencies score (10%)
            if metadata.validation_result.dependencies_satisfied:
                node_score += 10.0

            total_score += node_score

        return total_score / len(self.node_metadata)

    @field_validator("max_nodes")
    @classmethod
    def validate_max_nodes(cls, v, info):
        """Validate maximum nodes limit."""
        if v < 1 or v > 1000:
            msg = "max_nodes must be between 1 and 1000"
            raise ValueError(msg)
        return v

    def register_node(self, name: str, node_class: Any, **metadata_kwargs) -> bool:
        """Register a node implementation with comprehensive validation and metadata."""
        try:
            # Check collection limits
            if len(self.nodes) >= self.max_nodes:
                return False

            # Validate node implementation
            validation_result = self._validate_node(node_class)

            if self.strict_mode and not validation_result.is_valid:
                return False

            # Register the node
            self.nodes[name] = node_class

            # Create comprehensive metadata
            metadata = ModelNodeMetadata(
                name=name,
                node_class=node_class.__name__,
                module_path=node_class.__module__,
                validation_result=validation_result,
                **metadata_kwargs,
            )

            # Auto-detect category from class or module name
            if metadata.category == NodeCategory.CUSTOM:
                metadata.category = self._detect_node_category(node_class)

            self.node_metadata[name] = metadata

            # Update collection statistics
            self.total_registrations += 1
            self.active_node_count = len(
                [
                    m
                    for m in self.node_metadata.values()
                    if m.status == NodeRegistrationStatus.REGISTERED
                ],
            )
            self.last_modified = datetime.now()

            return True

        except Exception:
            self.failed_registration_count += 1
            return False

    def _validate_node(self, node_class: Any) -> ModelNodeValidationResult:
        """Validate node implementation against ProtocolNode interface."""
        result = ModelNodeValidationResult()

        try:
            # Check if it's a class
            if not inspect.isclass(node_class):
                result.is_valid = False
                result.validation_errors.append("Node must be a class")
                return result

            # Check ProtocolNode inheritance/compliance
            if not hasattr(node_class, "__annotations__"):
                result.interface_compliance = False
                result.validation_warnings.append("Node class lacks type annotations")

            # Check for required methods (basic ProtocolNode interface)
            required_methods = ["execute", "__init__"]
            for method_name in required_methods:
                if not hasattr(node_class, method_name):
                    result.is_valid = False
                    result.validation_errors.append(
                        f"Missing required method: {method_name}",
                    )

            # Validate method signatures
            if hasattr(node_class, "execute"):
                sig = inspect.signature(node_class.execute)
                if len(sig.parameters) < 1:  # Should have self at minimum
                    result.signature_valid = False
                    result.validation_warnings.append(
                        "execute method signature may be invalid",
                    )

            # Check for common issues
            if node_class.__name__.startswith("_"):
                result.validation_warnings.append(
                    "Node class name starts with underscore (private)",
                )

        except Exception as e:
            result.is_valid = False
            result.validation_errors.append(f"Validation failed: {e!s}")

        return result

    def _detect_node_category(self, node_class: Any) -> NodeCategory:
        """Auto-detect node category from class or module name."""
        class_name = node_class.__name__.lower()
        module_name = node_class.__module__.lower()

        # Category detection based on naming patterns
        if "registry" in class_name or "registry" in module_name:
            return NodeCategory.REGISTRY
        if "validate" in class_name or "validator" in class_name:
            return NodeCategory.VALIDATION
        if "transform" in class_name or "convert" in class_name:
            return NodeCategory.TRANSFORMATION
        if "output" in class_name or "format" in class_name:
            return NodeCategory.OUTPUT
        if "core" in module_name or "essential" in class_name:
            return NodeCategory.CORE
        if "util" in class_name or "helper" in class_name:
            return NodeCategory.UTILITY
        return NodeCategory.CUSTOM

    def get_node(self, name: str) -> Any | None:
        """Get a node implementation by name."""
        return self.nodes.get(name)

    def get_performance_summary(self) -> ModelPerformanceSummary:
        """Get comprehensive performance summary for all nodes."""
        if not self.node_metadata:
            return ModelPerformanceSummary(total_nodes=0, summary="No nodes registered")

        total_executions = sum(
            m.performance_metrics.total_executions for m in self.node_metadata.values()
        )
        avg_success_rate = sum(
            m.performance_metrics.success_rate_percent
            for m in self.node_metadata.values()
        ) / len(self.node_metadata)
        avg_execution_time = sum(
            m.performance_metrics.avg_execution_time_ms
            for m in self.node_metadata.values()
        ) / len(self.node_metadata)

        return ModelPerformanceSummary(
            total_nodes=len(self.nodes),
            active_nodes=self.active_node_count,
            deprecated_nodes=self.deprecated_node_count,
            total_executions=total_executions,
            avg_success_rate_percent=avg_success_rate,
            avg_execution_time_ms=avg_execution_time,
            collection_health_score=self.collection_health_score,
            nodes_by_category=self.node_count_by_category,
            nodes_by_status=self.node_count_by_status,
        )

    def has_node(self, name: str) -> bool:
        """Check if a node is registered."""
        return name in self.nodes

    def __contains__(self, name: str) -> bool:
        """Support 'in' operator."""
        return self.has_node(name)

    def __getitem__(self, name: str) -> Any:
        """Support dict-like access."""
        node = self.get_node(name)
        if node is None:
            msg = f"Node '{name}' not found in collection"
            raise KeyError(msg)
        return node

    def __setitem__(self, name: str, node_class: Any) -> None:
        """Support dict-like assignment."""
        self.register_node(name, node_class)

    def keys(self) -> None:
        """Support dict-like keys() method."""
        return self.nodes.keys()

    def values(self) -> None:
        """Support dict-like values() method."""
        return self.nodes.values()

    def items(self) -> None:
        """Support dict-like items() method."""
        return self.nodes.items()

    # Factory methods for common scenarios
    @classmethod
    def create_empty_collection(
        cls,
        name: str = "default",
        strict_mode: bool = False,
        max_nodes: int = 100,
    ) -> "ModelNodeCollection":
        """Create an empty node collection with specified configuration."""
        return cls(collection_name=name, strict_mode=strict_mode, max_nodes=max_nodes)

    @classmethod
    def create_from_nodes_dict(
        cls,
        nodes_dict: dict[str, Any],
        collection_name: str = "imported",
        auto_validate: bool = True,
    ) -> "ModelNodeCollection":
        """Create collection from existing nodes dictionary."""
        collection = cls(collection_name=collection_name, auto_validation=auto_validate)

        for name, node_class in nodes_dict.items():
            collection.register_node(name, node_class)

        return collection

    @classmethod
    def create_production_collection(
        cls,
        name: str,
        max_nodes: int = 50,
    ) -> "ModelNodeCollection":
        """Create a production-ready collection with strict validation."""
        return cls(
            collection_name=name,
            strict_mode=True,
            auto_validation=True,
            performance_monitoring=True,
            max_nodes=max_nodes,
        )


# Compatibility aliases
NodePerformanceMetrics = ModelNodePerformanceMetrics
NodeValidationResult = ModelNodeValidationResult
NodeMetadata = ModelNodeMetadata
NodeCollection = ModelNodeCollection

# Re-export for current standards
__all__ = [
    "ModelNodeCollection",
    "ModelNodeMetadata",
    "ModelNodePerformanceMetrics",
    "ModelNodeValidationResult",
    "NodeCapabilityLevel",
    "NodeCategory",
    "NodeCollection",
    "NodeCompatibilityMode",
    "NodeMetadata",
    # Compatibility
    "NodePerformanceMetrics",
    "NodeRegistrationStatus",
    "NodeValidationResult",
]
