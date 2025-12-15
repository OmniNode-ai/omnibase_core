from pydantic import Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

"""
Enterprise Missing Tool Model.

This module provides comprehensive missing tool tracking with business intelligence,
error analysis, and operational insights for ONEX registry validation systems.
"""

import re
from datetime import datetime

from pydantic import BaseModel

from omnibase_core.enums.enum_tool_category import EnumToolCategory
from omnibase_core.enums.enum_tool_criticality import EnumToolCriticality
from omnibase_core.enums.enum_tool_missing_reason import EnumToolMissingReason
from omnibase_core.models.core.model_protocol_metadata import ModelGenericMetadata
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.typed_dict_alert_data import TypedDictAlertData
from omnibase_core.types.typed_dict_alert_metadata import TypedDictAlertMetadata
from omnibase_core.types.typed_dict_error_analysis import TypedDictErrorAnalysis
from omnibase_core.types.typed_dict_monitoring_metrics import TypedDictMonitoringMetrics
from omnibase_core.types.typed_dict_operational_impact import TypedDictOperationalImpact
from omnibase_core.types.typed_dict_tool_details import TypedDictToolDetails


class ModelMissingTool(BaseModel):
    """
    Enterprise-grade missing tool tracking with comprehensive error analysis,
    business intelligence, and operational insights.

    Features:
    - Detailed tool classification and criticality assessment
    - Error analysis with categorized reasons and recovery recommendations
    - Business impact assessment and operational insights
    - Dependency tracking and conflict resolution
    - Security analysis and risk assessment
    - Performance impact evaluation
    - Monitoring integration with structured metrics
    - Factory methods for common scenarios
    """

    tool_name: str = Field(
        default=...,
        description="Name of the missing tool",
        min_length=1,
        max_length=200,
    )

    reason: str = Field(
        default=...,
        description="Detailed reason why the tool is missing or invalid",
        min_length=1,
        max_length=1000,
    )

    expected_type: str = Field(
        default=...,
        description="Expected type annotation for the tool",
        min_length=1,
        max_length=500,
    )

    reason_category: EnumToolMissingReason | None = Field(
        default=EnumToolMissingReason.NOT_FOUND,
        description="Categorized reason for missing tool",
    )

    criticality: EnumToolCriticality | None = Field(
        default=EnumToolCriticality.MEDIUM,
        description="Business criticality level of the missing tool",
    )

    tool_category: EnumToolCategory | None = Field(
        default=EnumToolCategory.UTILITY,
        description="Functional category of the missing tool",
    )

    expected_interface: str | None = Field(
        default=None,
        description="Expected protocol or interface the tool should implement",
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
        description="Suggested solution to resolve the missing tool",
        max_length=1000,
    )

    dependencies: list[str] | None = Field(
        default_factory=list,
        description="List of dependencies required for this tool",
    )

    alternative_tools: list[str] | None = Field(
        default_factory=list,
        description="Alternative tools that could provide similar functionality",
    )

    first_detected: str | None = Field(
        default=None,
        description="ISO timestamp when this issue was first detected",
    )

    detection_count: int | None = Field(
        default=1,
        description="Number of times this tool was detected as missing",
        ge=1,
    )

    metadata: ModelGenericMetadata | None = Field(
        default_factory=lambda: ModelGenericMetadata(
            version=ModelSemVer(major=1, minor=0, patch=0)
        ),
        description="Additional metadata and context information",
    )

    affected_operations: list[str] | None = Field(
        default_factory=list,
        description="List of operations affected by this missing tool",
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

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        """Validate tool name format."""
        if not v.strip():
            msg = "Tool name cannot be empty"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        # Check for valid Python identifier-like names (allow dots and hyphens)
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_\.\-]*$", v.strip()):
            msg = "Tool name should be a valid identifier-like string"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        return v.strip()

    @field_validator("expected_type")
    @classmethod
    def validate_expected_type(cls, v: str) -> str:
        """Validate expected type format."""
        if not v.strip():
            msg = "Expected type cannot be empty"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

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
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

    # === Classification and Analysis ===

    def is_critical_tool(self) -> bool:
        """Check if this is a critical tool."""
        return self.criticality == EnumToolCriticality.CRITICAL

    def is_high_priority_tool(self) -> bool:
        """Check if this is a high priority tool."""
        return self.criticality in [
            EnumToolCriticality.CRITICAL,
            EnumToolCriticality.HIGH,
        ]

    def is_core_tool(self) -> bool:
        """Check if this is a core system tool."""
        return self.tool_category == EnumToolCategory.CORE

    def is_integration_tool(self) -> bool:
        """Check if this is an integration tool."""
        return self.tool_category == EnumToolCategory.INTEGRATION

    def requires_immediate_attention(self) -> bool:
        """Check if this missing tool requires immediate attention."""
        return (
            self.is_critical_tool()
            or self.reason_category == EnumToolMissingReason.PERMISSION_DENIED
            or (
                self.business_impact_score is not None
                and self.business_impact_score > 0.8
            )
        )

    def get_severity_level(self) -> str:
        """Get overall severity level combining criticality and impact."""
        if self.is_critical_tool():
            return "CRITICAL"
        if self.criticality == EnumToolCriticality.HIGH or self.reason_category in [
            EnumToolMissingReason.PERMISSION_DENIED,
        ]:
            return "HIGH"
        if self.criticality == EnumToolCriticality.MEDIUM:
            return "MEDIUM"
        return "LOW"

    # === Error Analysis ===

    def analyze_error_category(self) -> TypedDictErrorAnalysis:
        """Analyze the error category and provide insights."""
        return TypedDictErrorAnalysis(
            category=(
                self.reason_category.value
                if self.reason_category is not None
                else "UNKNOWN"
            ),
            is_recoverable=self._is_recoverable_error(),
            requires_code_change=self._requires_code_change(),
            requires_configuration=self._requires_configuration_change(),
            estimated_fix_time=self._estimate_fix_time(),
            fix_complexity=self._assess_fix_complexity(),
        )

    def _is_recoverable_error(self) -> bool:
        """Check if the error is recoverable."""
        recoverable_reasons = [
            EnumToolMissingReason.CONFIGURATION_INVALID,
            EnumToolMissingReason.DEPENDENCY_MISSING,
            EnumToolMissingReason.PERMISSION_DENIED,
            EnumToolMissingReason.IMPORT_ERROR,
        ]
        return self.reason_category in recoverable_reasons

    def _requires_code_change(self) -> bool:
        """Check if fixing this requires code changes."""
        code_change_reasons = [
            EnumToolMissingReason.TYPE_MISMATCH,
            EnumToolMissingReason.PROTOCOL_VIOLATION,
            EnumToolMissingReason.CIRCULAR_DEPENDENCY,
            EnumToolMissingReason.VERSION_INCOMPATIBLE,
        ]
        return self.reason_category in code_change_reasons

    def _requires_configuration_change(self) -> bool:
        """Check if fixing this requires configuration changes."""
        config_change_reasons = [
            EnumToolMissingReason.CONFIGURATION_INVALID,
            EnumToolMissingReason.DEPENDENCY_MISSING,
            EnumToolMissingReason.PERMISSION_DENIED,
        ]
        return self.reason_category in config_change_reasons

    def _estimate_fix_time(self) -> str:
        """Estimate time required to fix this issue."""
        if self.reason_category == EnumToolMissingReason.NOT_FOUND:
            return "1-4 hours"  # Need to implement
        if self.reason_category == EnumToolMissingReason.CONFIGURATION_INVALID:
            return "15-30 minutes"  # Config fix
        if self.reason_category == EnumToolMissingReason.DEPENDENCY_MISSING:
            return "30-60 minutes"  # Install dependencies
        if self.reason_category == EnumToolMissingReason.TYPE_MISMATCH:
            return "2-6 hours"  # Code refactoring
        if self.reason_category == EnumToolMissingReason.PROTOCOL_VIOLATION:
            return "4-8 hours"  # Interface compliance
        if self.reason_category == EnumToolMissingReason.CIRCULAR_DEPENDENCY:
            return "8-16 hours"  # ModelArchitecture fix
        return "1-2 hours"  # General estimate

    def _assess_fix_complexity(self) -> str:
        """Assess the complexity of fixing this issue."""
        if self.reason_category in [
            EnumToolMissingReason.CIRCULAR_DEPENDENCY,
            EnumToolMissingReason.PROTOCOL_VIOLATION,
        ]:
            return "HIGH"
        if self.reason_category in [
            EnumToolMissingReason.TYPE_MISMATCH,
            EnumToolMissingReason.VERSION_INCOMPATIBLE,
        ]:
            return "MEDIUM"
        return "LOW"

    # === Recovery Recommendations ===

    def get_recovery_recommendations(self) -> list[str]:
        """Get prioritized recovery recommendations."""
        recommendations = []

        if self.reason_category == EnumToolMissingReason.NOT_FOUND:
            recommendations.append(
                "Implement the missing tool with the expected interface",
            )
            recommendations.append("Check if tool is defined in a different module")
            recommendations.append("Verify tool registration in the registry")

        elif self.reason_category == EnumToolMissingReason.TYPE_MISMATCH:
            recommendations.append(
                f"Update tool implementation to match expected type: {self.expected_type}",
            )
            recommendations.append("Check if tool interface has changed")
            recommendations.append(
                "Consider using adapter pattern for current standards"
            )

        elif self.reason_category == EnumToolMissingReason.IMPORT_ERROR:
            recommendations.append("Check import paths and module availability")
            recommendations.append("Verify all dependencies are installed")
            recommendations.append("Check for circular import issues")

        elif self.reason_category == EnumToolMissingReason.DEPENDENCY_MISSING:
            recommendations.append("Install missing dependencies")
            recommendations.append("Update requirements.txt or pyproject.toml")
            recommendations.append("Check dependency version compatibility")

        elif self.reason_category == EnumToolMissingReason.CONFIGURATION_INVALID:
            recommendations.append("Review and fix tool configuration")
            recommendations.append("Validate configuration against schema")
            recommendations.append("Check environment variable settings")

        elif self.reason_category == EnumToolMissingReason.PERMISSION_DENIED:
            recommendations.append("Check file and directory permissions")
            recommendations.append("Verify user has required access rights")
            recommendations.append("Consider running with appropriate privileges")

        # Add alternative solutions if available
        if self.alternative_tools:
            recommendations.append(
                f"Consider using alternative tools: {', '.join(self.alternative_tools)}",
            )

        # Add suggested solution if provided
        if self.suggested_solution:
            recommendations.insert(0, self.suggested_solution)

        return recommendations

    def get_debugging_steps(self) -> list[str]:
        """Get debugging steps to investigate this issue."""
        steps = [
            f"Verify tool '{self.tool_name}' is correctly registered",
            f"Check expected type annotation: {self.expected_type}",
            "Review recent code changes that might affect tool availability",
        ]

        if self.dependencies:
            steps.append(
                f"Verify dependencies are available: {', '.join(self.dependencies)}",
            )

        if self.error_details:
            steps.append("Review detailed error message for specific clues")

        steps.extend(
            [
                "Check tool implementation for interface compliance",
                "Verify tool can be instantiated independently",
                "Check for conflicting tool registrations",
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
            EnumToolCriticality.CRITICAL: 1.0,
            EnumToolCriticality.HIGH: 0.8,
            EnumToolCriticality.MEDIUM: 0.5,
            EnumToolCriticality.LOW: 0.3,
            EnumToolCriticality.OPTIONAL: 0.1,
        }
        score += criticality_scores.get(
            (
                self.criticality
                if self.criticality is not None
                else EnumToolCriticality.MEDIUM
            ),
            0.5,
        )

        # Adjust for tool category
        category_multipliers = {
            EnumToolCategory.CORE: 1.0,
            EnumToolCategory.SECURITY: 0.9,
            EnumToolCategory.INTEGRATION: 0.8,
            EnumToolCategory.BUSINESS_LOGIC: 0.7,
            EnumToolCategory.VALIDATION: 0.6,
            EnumToolCategory.MONITORING: 0.5,
            EnumToolCategory.PERFORMANCE: 0.5,
            EnumToolCategory.DATA_PROCESSING: 0.6,
            EnumToolCategory.EXTERNAL_SERVICE: 0.7,
            EnumToolCategory.UTILITY: 0.3,
        }
        if self.tool_category is not None:
            score *= category_multipliers.get(self.tool_category, 0.5)
        else:
            score *= 0.5

        # Adjust for affected operations
        if self.affected_operations:
            operation_impact = min(len(self.affected_operations) * 0.1, 0.3)
            score += operation_impact

        # Adjust for detection frequency
        if self.detection_count and self.detection_count > 1:
            frequency_penalty = min((self.detection_count - 1) * 0.1, 0.2)
            score += frequency_penalty

        return min(score, 1.0)

    def assess_operational_impact(self) -> TypedDictOperationalImpact:
        """Assess operational impact of this missing tool."""
        return TypedDictOperationalImpact(
            business_impact_score=self.calculate_business_impact_score(),
            severity_level=self.get_severity_level(),
            affected_operations_count=(
                len(self.affected_operations) if self.affected_operations else 0
            ),
            requires_immediate_attention=self.requires_immediate_attention(),
            estimated_downtime=self._estimate_downtime(),
            user_experience_impact=self._assess_user_experience_impact(),
            system_stability_risk=self._assess_stability_risk(),
        )

    def _estimate_downtime(self) -> str:
        """Estimate potential downtime impact."""
        if self.is_critical_tool():
            return "Immediate service disruption"
        if self.criticality == EnumToolCriticality.HIGH:
            return "Major functionality impacted"
        if self.criticality == EnumToolCriticality.MEDIUM:
            return "Some features unavailable"
        return "Minimal impact"

    def _assess_user_experience_impact(self) -> str:
        """Assess impact on user experience."""
        if self.is_critical_tool():
            return "Severe degradation"
        if self.tool_category == EnumToolCategory.SECURITY:
            return "Security concerns"
        if self.criticality == EnumToolCriticality.HIGH:
            return "Significant degradation"
        if self.criticality == EnumToolCriticality.MEDIUM:
            return "Moderate impact"
        return "Minor impact"

    def _assess_stability_risk(self) -> str:
        """Assess system stability risk."""
        if self.reason_category == EnumToolMissingReason.CIRCULAR_DEPENDENCY:
            return "High stability risk"
        if self.is_critical_tool():
            return "System instability likely"
        if self.tool_category == EnumToolCategory.CORE:
            return "Moderate stability risk"
        return "Low stability risk"

    # === Monitoring Integration ===

    def get_monitoring_metrics(self) -> TypedDictMonitoringMetrics:
        """Get comprehensive metrics for monitoring systems."""
        error_analysis = self.analyze_error_category()
        return TypedDictMonitoringMetrics(
            tool_name=self.tool_name,
            reason_category=(
                self.reason_category.value
                if self.reason_category is not None
                else "UNKNOWN"
            ),
            criticality=(
                self.criticality.value if self.criticality is not None else "UNKNOWN"
            ),
            tool_category=(
                self.tool_category.value
                if self.tool_category is not None
                else "UNKNOWN"
            ),
            severity_level=self.get_severity_level(),
            business_impact_score=self.calculate_business_impact_score(),
            requires_immediate_attention=self.requires_immediate_attention(),
            is_critical_tool=self.is_critical_tool(),
            is_recoverable=error_analysis["is_recoverable"],
            fix_complexity=error_analysis["fix_complexity"],
            detection_count=self.detection_count or 1,
            affected_operations_count=(
                len(self.affected_operations) if self.affected_operations else 0
            ),
            has_alternatives=bool(self.alternative_tools),
            has_dependencies=bool(self.dependencies),
            first_detected=self.first_detected,
        )

    def get_alert_data(self) -> TypedDictAlertData:
        """Get structured data for alerting systems."""
        return TypedDictAlertData(
            alert_level=self.get_severity_level(),
            title=f"Missing Tool: {self.tool_name}",
            description=self.reason,
            tool_details=TypedDictToolDetails(
                name=self.tool_name,
                expected_type=self.expected_type,
                category=(
                    self.tool_category.value
                    if self.tool_category is not None
                    else "UNKNOWN"
                ),
                criticality=(
                    self.criticality.value
                    if self.criticality is not None
                    else "UNKNOWN"
                ),
            ),
            impact_assessment=self.assess_operational_impact(),
            recovery_recommendations=self.get_recovery_recommendations()[:3],  # Top 3
            metadata=TypedDictAlertMetadata(
                reason_category=(
                    self.reason_category.value
                    if self.reason_category is not None
                    else "UNKNOWN"
                ),
                detection_count=self.detection_count,
                first_detected=self.first_detected,
            ),
        )

    # === Factory Methods ===

    @classmethod
    def create_not_found(
        cls,
        tool_name: str,
        expected_type: str,
        criticality: EnumToolCriticality = EnumToolCriticality.MEDIUM,
    ) -> "ModelMissingTool":
        """Create a missing tool entry for a tool that was not found."""
        return cls(
            tool_name=tool_name,
            reason=f"Tool '{tool_name}' was not found in the registry",
            expected_type=expected_type,
            reason_category=EnumToolMissingReason.NOT_FOUND,
            criticality=criticality,
            suggested_solution=f"Implement and register tool '{tool_name}' with type {expected_type}",
        )

    @classmethod
    def create_type_mismatch(
        cls,
        tool_name: str,
        expected_type: str,
        actual_type: str,
        criticality: EnumToolCriticality = EnumToolCriticality.MEDIUM,
    ) -> "ModelMissingTool":
        """Create a missing tool entry for type mismatch."""
        return cls(
            tool_name=tool_name,
            reason=f"Tool '{tool_name}' type mismatch: expected {expected_type}, got {actual_type}",
            expected_type=expected_type,
            actual_type_found=actual_type,
            reason_category=EnumToolMissingReason.TYPE_MISMATCH,
            criticality=criticality,
            suggested_solution=f"Update tool '{tool_name}' to implement {expected_type} interface",
        )

    @classmethod
    def create_import_error(
        cls,
        tool_name: str,
        expected_type: str,
        error_details: str,
        dependencies: list[str] | None = None,
    ) -> "ModelMissingTool":
        """Create a missing tool entry for import errors."""
        return cls(
            tool_name=tool_name,
            reason=f"Failed to import tool '{tool_name}': {error_details}",
            expected_type=expected_type,
            error_details=error_details,
            reason_category=EnumToolMissingReason.IMPORT_ERROR,
            criticality=EnumToolCriticality.HIGH,
            dependencies=dependencies if dependencies is not None else [],
            suggested_solution="Fix import issues and ensure all dependencies are available",
        )

    @classmethod
    def create_permission_denied(
        cls,
        tool_name: str,
        expected_type: str,
        criticality: EnumToolCriticality = EnumToolCriticality.HIGH,
    ) -> "ModelMissingTool":
        """Create a missing tool entry for permission issues."""
        return cls(
            tool_name=tool_name,
            reason=f"Permission denied accessing tool '{tool_name}'",
            expected_type=expected_type,
            reason_category=EnumToolMissingReason.PERMISSION_DENIED,
            criticality=criticality,
            tool_category=EnumToolCategory.SECURITY,
            suggested_solution="Check file permissions and user access rights",
        )

    @classmethod
    def create_dependency_missing(
        cls,
        tool_name: str,
        expected_type: str,
        missing_dependencies: list[str],
    ) -> "ModelMissingTool":
        """Create a missing tool entry for missing dependencies."""
        deps_str = ", ".join(missing_dependencies)
        return cls(
            tool_name=tool_name,
            reason=f"Tool '{tool_name}' cannot be loaded due to missing dependencies: {deps_str}",
            expected_type=expected_type,
            reason_category=EnumToolMissingReason.DEPENDENCY_MISSING,
            criticality=EnumToolCriticality.MEDIUM,
            dependencies=missing_dependencies,
            suggested_solution=f"Install missing dependencies: {deps_str}",
        )

    @classmethod
    def create_from_exception(
        cls,
        tool_name: str,
        expected_type: str,
        exception: Exception,
    ) -> "ModelMissingTool":
        """Create a missing tool entry from an exception."""
        error_type = type(exception).__name__
        error_msg = str(exception)

        # Determine reason category based on exception type
        if "ImportError" in error_type or "ModuleNotFoundError" in error_type:
            reason_category = EnumToolMissingReason.IMPORT_ERROR
        elif "TypeError" in error_type:
            reason_category = EnumToolMissingReason.TYPE_MISMATCH
        elif "PermissionError" in error_type:
            reason_category = EnumToolMissingReason.PERMISSION_DENIED
        else:
            reason_category = EnumToolMissingReason.INSTANTIATION_FAILED

        return cls(
            tool_name=tool_name,
            reason=f"Tool '{tool_name}' failed with {error_type}: {error_msg}",
            expected_type=expected_type,
            error_details=f"{error_type}: {error_msg}",
            reason_category=reason_category,
            criticality=EnumToolCriticality.HIGH,
            suggested_solution=f"Fix {error_type} in tool '{tool_name}' implementation",
        )
