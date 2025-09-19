"""
Enterprise Missing Node Model.

This module provides comprehensive missing node tracking with business intelligence,
error analysis, and operational insights for ONEX registry validation systems.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .model_generic_metadata import ModelGenericMetadata
from .model_monitoring_metrics import ModelMonitoringMetrics


class NodeMissingReason(str, Enum):
    """Categorized reasons for missing nodes."""

    NOT_FOUND = "not_found"
    TYPE_MISMATCH = "type_mismatch"
    IMPORT_ERROR = "import_error"
    INSTANTIATION_FAILED = "instantiation_failed"
    PERMISSION_DENIED = "permission_denied"
    DEPENDENCY_MISSING = "dependency_missing"
    VERSION_INCOMPATIBLE = "version_incompatible"
    CONFIGURATION_INVALID = "configuration_invalid"
    PROTOCOL_VIOLATION = "protocol_violation"
    CIRCULAR_DEPENDENCY = "circular_dependency"


class NodeCriticality(str, Enum):
    """Node criticality levels for business impact assessment."""

    CRITICAL = "critical"  # System cannot function
    HIGH = "high"  # Major functionality impacted
    MEDIUM = "medium"  # Some functionality impacted
    LOW = "low"  # Minor functionality impacted
    OPTIONAL = "optional"  # Nice-to-have functionality


class NodeCategory(str, Enum):
    """Node category classification."""

    CORE = "core"
    INTEGRATION = "integration"
    UTILITY = "utility"
    VALIDATION = "validation"
    MONITORING = "monitoring"
    SECURITY = "security"
    PERFORMANCE = "performance"
    BUSINESS_LOGIC = "business_logic"
    DATA_PROCESSING = "data_processing"
    EXTERNAL_SERVICE = "external_service"


class ModelMissingNode(BaseModel):
    """
    Enterprise-grade missing node tracking with comprehensive error analysis,
    business intelligence, and operational insights.

    Features:
    - Detailed node classification and criticality assessment
    - Error analysis with categorized reasons and recovery recommendations
    - Business impact assessment and operational insights
    - Dependency tracking and conflict resolution
    - Security analysis and risk assessment
    - Performance impact evaluation
    - Monitoring integration with structured metrics
    - Factory methods for common scenarios
    """

    node_name: str = Field(
        ...,
        description="Name of the missing node",
        min_length=1,
        max_length=200,
    )

    reason: str = Field(
        ...,
        description="Detailed reason why the node is missing or invalid",
        min_length=1,
        max_length=1000,
    )

    expected_type: str = Field(
        ...,
        description="Expected type annotation for the node",
        min_length=1,
        max_length=500,
    )

    reason_category: NodeMissingReason | None = Field(
        default=NodeMissingReason.NOT_FOUND,
        description="Categorized reason for missing node",
    )

    criticality: NodeCriticality | None = Field(
        default=NodeCriticality.MEDIUM,
        description="Business criticality level of the missing node",
    )

    node_category: NodeCategory | None = Field(
        default=NodeCategory.UTILITY,
        description="Functional category of the missing node",
    )

    expected_interface: str | None = Field(
        default=None,
        description="Expected protocol or interface the node should implement",
        max_length=300,
    )

    actual_type_found: str | None = Field(
        default=None,
        description="Actual type found if any (for type mismatches)",
        max_length=500,
    )

    error_details: str | None = Field(
        default=None,
        description="Detailed error message or stack trace",
        max_length=2000,
    )

    suggested_solution: str | None = Field(
        default=None,
        description="Suggested solution to resolve the missing node",
        max_length=1000,
    )

    dependencies: list[str] | None = Field(
        default_factory=lambda: [],
        description="List of dependencies required for this node",
    )

    alternative_nodes: list[str] | None = Field(
        default_factory=lambda: [],
        description="Alternative nodes that could provide similar functionality",
    )

    first_detected: str | None = Field(
        default=None,
        description="ISO timestamp when this issue was first detected",
    )

    detection_count: int | None = Field(
        default=1,
        description="Number of times this node was detected as missing",
        ge=1,
    )

    metadata: ModelGenericMetadata | None = Field(
        default_factory=lambda: ModelGenericMetadata(
            created_at=None,
            updated_at=None,
            created_by=None,
            updated_by=None,
            version=None,
            tags=None,
            labels=None,
            annotations=None,
            custom_fields=None,
            extended_data=None,
        ),
        description="Additional metadata and context information",
    )

    affected_operations: list[str] | None = Field(
        default_factory=lambda: [],
        description="List of operations affected by this missing node",
    )

    business_impact_score: float | None = Field(
        default=None,
        description="Business impact score (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )

    resolution_priority: int | None = Field(
        default=None,
        description="Resolution priority ranking (1-10, 1 being highest)",
        ge=1,
        le=10,
    )

    @field_validator("node_name")
    @classmethod
    def validate_node_name(cls, v: str) -> str:
        """Validate node name format."""
        if not v.strip():
            msg = "Node name cannot be empty"
            raise ValueError(msg)

        # Check for valid Python identifier-like names
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v.strip()):
            # Allow some flexibility for node names with dots or hyphens
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_\.\-]*$", v.strip()):  # type: ignore[unreachable]
                raise ValueError("Node name should be a valid identifier-like string")

        return v.strip()

    @field_validator("expected_type")
    @classmethod
    def validate_expected_type(cls, v: str) -> str:
        """Validate expected type format."""
        if not v.strip():
            msg = "Expected type cannot be empty"
            raise ValueError(msg)

        # Basic validation for Python type annotations
        # Allow common patterns like 'str', 'Optional[str]', 'Protocol[...]', etc.
        return v.strip()

    @field_validator("first_detected")
    @classmethod
    def validate_first_detected(cls, v: str | None) -> str | None:
        """Validate ISO timestamp format."""
        if v is None:
            return datetime.now().isoformat()

        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            msg = "first_detected must be a valid ISO timestamp"
            raise ValueError(msg)

    # === Classification and Analysis ===

    def is_critical_node(self) -> bool:
        """Check if this is a critical node."""
        return self.criticality == NodeCriticality.CRITICAL

    def is_high_priority_node(self) -> bool:
        """Check if this is a high priority node."""
        return self.criticality in [NodeCriticality.CRITICAL, NodeCriticality.HIGH]

    def is_core_node(self) -> bool:
        """Check if this is a core system node."""
        return self.node_category == NodeCategory.CORE

    def is_integration_node(self) -> bool:
        """Check if this is an integration node."""
        return self.node_category == NodeCategory.INTEGRATION

    def requires_immediate_attention(self) -> bool:
        """Check if this missing node requires immediate attention."""
        return (
            self.is_critical_node()
            or self.reason_category == NodeMissingReason.PERMISSION_DENIED
            or (
                self.business_impact_score is not None
                and self.business_impact_score > 0.8
            )
        )

    def get_severity_level(self) -> str:
        """Get overall severity level combining criticality and impact."""
        if self.is_critical_node():
            return "CRITICAL"
        if self.criticality == NodeCriticality.HIGH or self.reason_category in [
            NodeMissingReason.PERMISSION_DENIED,
            NodeMissingReason.PERMISSION_DENIED,
        ]:
            return "HIGH"
        if self.criticality == NodeCriticality.MEDIUM:
            return "MEDIUM"
        return "LOW"

    # === Error Analysis ===

    def analyze_error_category(self) -> dict[str, Any]:
        """Analyze the error category and provide insights."""
        return {
            "category": self.reason_category.value if self.reason_category else None,
            "is_recoverable": self._is_recoverable_error(),
            "requires_code_change": self._requires_code_change(),
            "requires_configuration": self._requires_configuration_change(),
            "estimated_fix_time": self._estimate_fix_time(),
            "fix_complexity": self._assess_fix_complexity(),
        }

    def _is_recoverable_error(self) -> bool:
        """Check if the error is recoverable."""
        recoverable_reasons = [
            NodeMissingReason.CONFIGURATION_INVALID,
            NodeMissingReason.DEPENDENCY_MISSING,
            NodeMissingReason.PERMISSION_DENIED,
            NodeMissingReason.IMPORT_ERROR,
        ]
        return self.reason_category in recoverable_reasons

    def _requires_code_change(self) -> bool:
        """Check if fixing this requires code changes."""
        code_change_reasons = [
            NodeMissingReason.TYPE_MISMATCH,
            NodeMissingReason.PROTOCOL_VIOLATION,
            NodeMissingReason.CIRCULAR_DEPENDENCY,
            NodeMissingReason.VERSION_INCOMPATIBLE,
        ]
        return self.reason_category in code_change_reasons

    def _requires_configuration_change(self) -> bool:
        """Check if fixing this requires configuration changes."""
        config_change_reasons = [
            NodeMissingReason.CONFIGURATION_INVALID,
            NodeMissingReason.DEPENDENCY_MISSING,
            NodeMissingReason.PERMISSION_DENIED,
        ]
        return self.reason_category in config_change_reasons

    def _estimate_fix_time(self) -> str:
        """Estimate time required to fix this issue."""
        if self.reason_category == NodeMissingReason.NOT_FOUND:
            return "1-4 hours"  # Need to implement
        if self.reason_category == NodeMissingReason.CONFIGURATION_INVALID:
            return "15-30 minutes"  # Config fix
        if self.reason_category == NodeMissingReason.DEPENDENCY_MISSING:
            return "30-60 minutes"  # Install dependencies
        if self.reason_category == NodeMissingReason.TYPE_MISMATCH:
            return "2-6 hours"  # Code refactoring
        if self.reason_category == NodeMissingReason.PROTOCOL_VIOLATION:
            return "4-8 hours"  # Interface compliance
        if self.reason_category == NodeMissingReason.CIRCULAR_DEPENDENCY:
            return "8-16 hours"  # Architecture fix
        return "1-2 hours"  # General estimate

    def _assess_fix_complexity(self) -> str:
        """Assess the complexity of fixing this issue."""
        if self.reason_category in [
            NodeMissingReason.CIRCULAR_DEPENDENCY,
            NodeMissingReason.PROTOCOL_VIOLATION,
        ]:
            return "HIGH"
        if self.reason_category in [
            NodeMissingReason.TYPE_MISMATCH,
            NodeMissingReason.VERSION_INCOMPATIBLE,
        ]:
            return "MEDIUM"
        return "LOW"

    # === Recovery Recommendations ===

    def get_recovery_recommendations(self) -> list[str]:
        """Get prioritized recovery recommendations."""
        recommendations = []

        if self.reason_category == NodeMissingReason.NOT_FOUND:
            recommendations.append(
                "Implement the missing node with the expected interface",
            )
            recommendations.append("Check if node is defined in a different module")
            recommendations.append("Verify node registration in the registry")

        elif self.reason_category == NodeMissingReason.TYPE_MISMATCH:
            recommendations.append(
                f"Update node implementation to match expected type: {self.expected_type}",
            )
            recommendations.append("Check if node interface has changed")
            recommendations.append(
                "Consider using adapter pattern for current standards"
            )

        elif self.reason_category == NodeMissingReason.IMPORT_ERROR:
            recommendations.append("Check import paths and module availability")
            recommendations.append("Verify all dependencies are installed")
            recommendations.append("Check for circular import issues")

        elif self.reason_category == NodeMissingReason.DEPENDENCY_MISSING:
            recommendations.append("Install missing dependencies")
            recommendations.append("Update requirements.txt or pyproject.toml")
            recommendations.append("Check dependency version compatibility")

        elif self.reason_category == NodeMissingReason.CONFIGURATION_INVALID:
            recommendations.append("Review and fix node configuration")
            recommendations.append("Validate configuration against schema")
            recommendations.append("Check environment variable settings")

        elif self.reason_category == NodeMissingReason.PERMISSION_DENIED:
            recommendations.append("Check file and directory permissions")
            recommendations.append("Verify user has required access rights")
            recommendations.append("Consider running with appropriate privileges")

        # Add alternative solutions if available
        if self.alternative_nodes:
            recommendations.append(
                f"Consider using alternative nodes: {', '.join(self.alternative_nodes)}",
            )

        # Add suggested solution if provided
        if self.suggested_solution:
            recommendations.insert(0, self.suggested_solution)

        return recommendations

    def get_debugging_steps(self) -> list[str]:
        """Get debugging steps to investigate this issue."""
        steps = [
            f"Verify node '{self.node_name}' is correctly registered",
            f"Check expected type annotation: {self.expected_type}",
            "Review recent code changes that might affect node availability",
        ]

        if self.dependencies:
            steps.append(
                f"Verify dependencies are available: {', '.join(self.dependencies)}",
            )

        if self.error_details:
            steps.append("Review detailed error message for specific clues")

        steps.extend(
            [
                "Check node implementation for interface compliance",
                "Verify node can be instantiated independently",
                "Check for conflicting node registrations",
            ],
        )

        return steps

    # === Business Intelligence ===

    def calculate_business_impact_score(self) -> float:
        """Calculate business impact score based on multiple factors."""
        if self.business_impact_score is not None:
            return self.business_impact_score

        score = 0.0

        # Base score from criticality
        criticality_scores = {
            NodeCriticality.CRITICAL: 1.0,
            NodeCriticality.HIGH: 0.8,
            NodeCriticality.MEDIUM: 0.5,
            NodeCriticality.LOW: 0.3,
            NodeCriticality.OPTIONAL: 0.1,
        }
        score += (
            criticality_scores.get(self.criticality, 0.5) if self.criticality else 0.5
        )

        # Adjust for node category
        category_multipliers = {
            NodeCategory.CORE: 1.0,
            NodeCategory.SECURITY: 0.9,
            NodeCategory.INTEGRATION: 0.8,
            NodeCategory.BUSINESS_LOGIC: 0.7,
            NodeCategory.VALIDATION: 0.6,
            NodeCategory.MONITORING: 0.5,
            NodeCategory.PERFORMANCE: 0.5,
            NodeCategory.DATA_PROCESSING: 0.6,
            NodeCategory.EXTERNAL_SERVICE: 0.7,
            NodeCategory.UTILITY: 0.3,
        }
        score *= (
            category_multipliers.get(self.node_category, 0.5)
            if self.node_category
            else 0.5
        )

        # Adjust for affected operations
        if self.affected_operations:
            operation_impact = min(len(self.affected_operations) * 0.1, 0.3)
            score += operation_impact

        # Adjust for detection frequency
        if self.detection_count and self.detection_count > 1:
            frequency_penalty = min((self.detection_count - 1) * 0.1, 0.2)
            score += frequency_penalty

        return min(score, 1.0)

    def assess_operational_impact(self) -> dict[str, Any]:
        """Assess operational impact of this missing node."""
        return {
            "business_impact_score": self.calculate_business_impact_score(),
            "severity_level": self.get_severity_level(),
            "affected_operations_count": (
                len(self.affected_operations) if self.affected_operations else 0
            ),
            "requires_immediate_attention": self.requires_immediate_attention(),
            "estimated_downtime": self._estimate_downtime(),
            "user_experience_impact": self._assess_user_experience_impact(),
            "system_stability_risk": self._assess_stability_risk(),
        }

    def _estimate_downtime(self) -> str:
        """Estimate potential downtime impact."""
        if self.is_critical_node():
            return "Immediate service disruption"
        if self.criticality == NodeCriticality.HIGH:
            return "Major functionality impacted"
        if self.criticality == NodeCriticality.MEDIUM:
            return "Some features unavailable"
        return "Minimal impact"

    def _assess_user_experience_impact(self) -> str:
        """Assess impact on user experience."""
        if self.is_critical_node():
            return "Severe degradation"
        if self.node_category == NodeCategory.SECURITY:
            return "Security concerns"
        if self.criticality == NodeCriticality.HIGH:
            return "Significant degradation"
        if self.criticality == NodeCriticality.MEDIUM:
            return "Moderate impact"
        return "Minor impact"

    def _assess_stability_risk(self) -> str:
        """Assess system stability risk."""
        if self.reason_category == NodeMissingReason.CIRCULAR_DEPENDENCY:
            return "High stability risk"
        if self.is_critical_node():
            return "System instability likely"
        if self.node_category == NodeCategory.CORE:
            return "Moderate stability risk"
        return "Low stability risk"

    # === Monitoring Integration ===

    def get_monitoring_metrics(self) -> dict[str, Any]:
        """Get comprehensive metrics for monitoring systems."""
        return {
            "node_name": self.node_name,
            "reason_category": (
                self.reason_category.value if self.reason_category else None
            ),
            "criticality": self.criticality.value if self.criticality else None,
            "node_category": self.node_category.value if self.node_category else None,
            "severity_level": self.get_severity_level(),
            "business_impact_score": self.calculate_business_impact_score(),
            "requires_immediate_attention": self.requires_immediate_attention(),
            "is_critical_node": self.is_critical_node(),
            "is_recoverable": self.analyze_error_category()["is_recoverable"],
            "fix_complexity": self.analyze_error_category()["fix_complexity"],
            "detection_count": self.detection_count or 1,
            "affected_operations_count": (
                len(self.affected_operations) if self.affected_operations else 0
            ),
            "has_alternatives": bool(self.alternative_nodes),
            "has_dependencies": bool(self.dependencies),
            "first_detected": self.first_detected,
        }

    def get_alert_data(self) -> dict[str, Any]:
        """Get structured data for alerting systems."""
        return {
            "alert_level": self.get_severity_level(),
            "title": f"Missing Node: {self.node_name}",
            "description": self.reason,
            "node_details": {
                "name": self.node_name,
                "expected_type": self.expected_type,
                "category": self.node_category.value if self.node_category else None,
                "criticality": self.criticality.value if self.criticality else None,
            },
            "impact_assessment": self.assess_operational_impact(),
            "recovery_recommendations": self.get_recovery_recommendations()[
                :3
            ],  # Top 3
            "metadata": {
                "reason_category": (
                    self.reason_category.value if self.reason_category else None
                ),
                "detection_count": self.detection_count,
                "first_detected": self.first_detected,
            },
        }

    # === Factory Methods ===

    @classmethod
    def create_not_found(
        cls,
        node_name: str,
        expected_type: str,
        criticality: NodeCriticality = NodeCriticality.MEDIUM,
    ) -> "ModelMissingNode":
        """Create a missing node entry for a node that was not found."""
        return cls(
            node_name=node_name,
            reason=f"Node '{node_name}' was not found in the registry",
            expected_type=expected_type,
            reason_category=NodeMissingReason.NOT_FOUND,
            criticality=criticality,
            suggested_solution=f"Implement and register node '{node_name}' with type {expected_type}",
        )

    @classmethod
    def create_type_mismatch(
        cls,
        node_name: str,
        expected_type: str,
        actual_type: str,
        criticality: NodeCriticality = NodeCriticality.MEDIUM,
    ) -> "ModelMissingNode":
        """Create a missing node entry for type mismatch."""
        return cls(
            node_name=node_name,
            reason=f"Node '{node_name}' type mismatch: expected {expected_type}, got {actual_type}",
            expected_type=expected_type,
            actual_type_found=actual_type,
            reason_category=NodeMissingReason.TYPE_MISMATCH,
            criticality=criticality,
            suggested_solution=f"Update node '{node_name}' to implement {expected_type} interface",
        )

    @classmethod
    def create_import_error(
        cls,
        node_name: str,
        expected_type: str,
        error_details: str,
        dependencies: list[str] | None = None,
    ) -> "ModelMissingNode":
        """Create a missing node entry for import errors."""
        return cls(
            node_name=node_name,
            reason=f"Failed to import node '{node_name}': {error_details}",
            expected_type=expected_type,
            error_details=error_details,
            reason_category=NodeMissingReason.IMPORT_ERROR,
            criticality=NodeCriticality.HIGH,
            dependencies=dependencies or [],
            suggested_solution="Fix import issues and ensure all dependencies are available",
        )

    @classmethod
    def create_permission_denied(
        cls,
        node_name: str,
        expected_type: str,
        criticality: NodeCriticality = NodeCriticality.HIGH,
    ) -> "ModelMissingNode":
        """Create a missing node entry for permission issues."""
        return cls(
            node_name=node_name,
            reason=f"Permission denied accessing node '{node_name}'",
            expected_type=expected_type,
            reason_category=NodeMissingReason.PERMISSION_DENIED,
            criticality=criticality,
            node_category=NodeCategory.SECURITY,
            suggested_solution="Check file permissions and user access rights",
        )

    @classmethod
    def create_dependency_missing(
        cls,
        node_name: str,
        expected_type: str,
        missing_dependencies: list[str],
    ) -> "ModelMissingNode":
        """Create a missing node entry for missing dependencies."""
        deps_str = ", ".join(missing_dependencies)
        return cls(
            node_name=node_name,
            reason=f"Node '{node_name}' cannot be loaded due to missing dependencies: {deps_str}",
            expected_type=expected_type,
            reason_category=NodeMissingReason.DEPENDENCY_MISSING,
            criticality=NodeCriticality.MEDIUM,
            dependencies=missing_dependencies,
            suggested_solution=f"Install missing dependencies: {deps_str}",
        )

    @classmethod
    def create_from_exception(
        cls,
        node_name: str,
        expected_type: str,
        exception: Exception,
    ) -> "ModelMissingNode":
        """Create a missing node entry from an exception."""
        error_type = type(exception).__name__
        error_msg = str(exception)

        # Determine reason category based on exception type
        if "ImportError" in error_type or "ModuleNotFoundError" in error_type:
            reason_category = NodeMissingReason.IMPORT_ERROR
        elif "TypeError" in error_type:
            reason_category = NodeMissingReason.TYPE_MISMATCH
        elif "PermissionError" in error_type:
            reason_category = NodeMissingReason.PERMISSION_DENIED
        else:
            reason_category = NodeMissingReason.INSTANTIATION_FAILED

        return cls(
            node_name=node_name,
            reason=f"Node '{node_name}' failed with {error_type}: {error_msg}",
            expected_type=expected_type,
            error_details=f"{error_type}: {error_msg}",
            reason_category=reason_category,
            criticality=NodeCriticality.HIGH,
            suggested_solution=f"Fix {error_type} in node '{node_name}' implementation",
        )
