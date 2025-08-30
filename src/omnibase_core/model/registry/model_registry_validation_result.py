"""
Enterprise Registry Validation Result Model.

This module provides comprehensive registry validation result tracking with business intelligence,
performance analytics, and operational insights for ONEX registry validation systems.
"""

import json
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional, Set

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from omnibase_core.model.core.model_generic_metadata import ModelGenericMetadata
    from omnibase_core.model.core.model_monitoring_metrics import ModelMonitoringMetrics
    from omnibase_core.model.core.model_audit_entry import ModelAuditEntry

from omnibase_core.model.core.model_missing_tool import (ModelMissingTool,
                                                         ToolCriticality)

from .model_registry_business_impact import ModelRegistryBusinessImpact
from .model_registry_business_risk import ModelRegistryBusinessRisk
from .model_registry_recovery_action import ModelRegistryRecoveryAction
from .model_registry_security_assessment import ModelRegistrySecurityAssessment


class ValidationStatus(str, Enum):
    """Registry validation status values."""

    VALID = "valid"
    INVALID = "invalid"
    PARTIAL = "partial"
    ERROR = "error"
    SKIPPED = "skipped"
    IN_PROGRESS = "in_progress"


class ValidationSeverity(str, Enum):
    """Validation issue severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ValidationType(str, Enum):
    """Types of validation performed."""

    TOOLS_VALIDATION = "tools_validation"
    INTERFACE_VALIDATION = "interface_validation"
    DEPENDENCY_VALIDATION = "dependency_validation"
    CONFIGURATION_VALIDATION = "configuration_validation"
    SECURITY_VALIDATION = "security_validation"
    PERFORMANCE_VALIDATION = "performance_validation"
    COMPLIANCE_VALIDATION = "compliance_validation"


class ModelRegistryValidationResult(BaseModel):
    """
    Enterprise-grade registry validation result with comprehensive analytics,
    business intelligence, and operational insights.

    Features:
    - Comprehensive validation status tracking and analytics
    - Missing tool analysis with business impact assessment
    - Performance monitoring and optimization insights
    - Error analysis and recovery recommendations
    - Business intelligence and operational metrics
    - Security and compliance validation
    - Audit trail and reporting capabilities
    - Factory methods for common scenarios
    """

    is_valid: bool = Field(..., description="Whether the registry passed validation")

    node_class_name: str = Field(
        ...,
        description="Name of the node class being validated against",
        min_length=1,
        max_length=300,
    )

    required_tools_count: int = Field(
        ..., description="Number of required tools for the node", ge=0
    )

    missing_tools: List[ModelMissingTool] = Field(
        default_factory=list, description="List of missing or invalid tools"
    )

    error_message: Optional[str] = Field(
        None, description="Error message if validation failed", max_length=2000
    )

    validation_status: Optional[ValidationStatus] = Field(
        default=None, description="Detailed validation status"
    )

    validation_types: Optional[List[ValidationType]] = Field(
        default_factory=list, description="Types of validation performed"
    )

    validation_start_time: Optional[str] = Field(
        default=None, description="ISO timestamp when validation started"
    )

    validation_end_time: Optional[str] = Field(
        default=None, description="ISO timestamp when validation completed"
    )

    validation_duration_ms: Optional[int] = Field(
        default=None, description="Validation duration in milliseconds", ge=0
    )

    available_tools_count: Optional[int] = Field(
        default=None, description="Number of tools that were available", ge=0
    )

    warnings: Optional[List[str]] = Field(
        default_factory=list, description="Non-fatal warnings during validation"
    )

    recommendations: Optional[List[str]] = Field(
        default_factory=list, description="Recommendations for improving registry"
    )

    metadata: Optional["ModelGenericMetadata"] = Field(
        None, description="Additional validation metadata"
    )

    severity_level: Optional[ValidationSeverity] = Field(
        default=None, description="Overall severity level of validation issues"
    )

    compliance_score: Optional[float] = Field(
        default=None, description="Compliance score (0.0 to 1.0)", ge=0.0, le=1.0
    )

    performance_metrics: Optional["ModelMonitoringMetrics"] = Field(
        None, description="Performance metrics from validation"
    )

    security_assessment: Optional[ModelRegistrySecurityAssessment] = Field(
        None, description="Security assessment results"
    )

    business_impact: Optional[ModelRegistryBusinessImpact] = Field(
        None, description="Business impact assessment"
    )

    @field_validator("validation_start_time", "validation_end_time")
    @classmethod
    def validate_timestamps(cls, v: Optional[str]) -> Optional[str]:
        """Validate ISO timestamp format."""
        if v is None:
            return v

        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError("Timestamp must be a valid ISO timestamp")

    def __init__(self, **data):
        super().__init__(**data)
        # Auto-set validation status if not provided
        if self.validation_status is None:
            self.validation_status = (
                ValidationStatus.VALID if self.is_valid else ValidationStatus.INVALID
            )

        # Auto-calculate severity if not provided
        if self.severity_level is None:
            self.severity_level = self._calculate_severity_level()

    # === Status and Success Analysis ===

    def is_successful(self) -> bool:
        """Check if validation was successful."""
        return self.is_valid and self.validation_status == ValidationStatus.VALID

    def is_failed(self) -> bool:
        """Check if validation failed."""
        return not self.is_valid or self.validation_status == ValidationStatus.INVALID

    def has_critical_issues(self) -> bool:
        """Check if there are critical validation issues."""
        return self.severity_level == ValidationSeverity.CRITICAL or any(
            tool.is_critical_tool() for tool in self.missing_tools
        )

    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return bool(self.warnings)

    def has_missing_tools(self) -> bool:
        """Check if there are missing tools."""
        return bool(self.missing_tools)

    def get_missing_tools_count(self) -> int:
        """Get count of missing tools."""
        return len(self.missing_tools)

    def get_success_rate(self) -> float:
        """Calculate success rate as percentage of available tools."""
        if self.required_tools_count == 0:
            return 1.0

        available_count = self.available_tools_count or (
            self.required_tools_count - self.get_missing_tools_count()
        )
        return available_count / self.required_tools_count

    def get_completion_percentage(self) -> float:
        """Get completion percentage (0.0 to 100.0)."""
        return self.get_success_rate() * 100.0

    # === Performance Analysis ===

    def get_validation_duration_seconds(self) -> Optional[float]:
        """Get validation duration in seconds."""
        if self.validation_duration_ms is None:
            return None
        return self.validation_duration_ms / 1000.0

    def get_validation_performance_category(self) -> str:
        """Categorize validation performance."""
        if self.validation_duration_ms is None:
            return "unknown"

        seconds = self.get_validation_duration_seconds()

        if seconds < 0.1:
            return "excellent"
        elif seconds < 0.5:
            return "good"
        elif seconds < 2.0:
            return "acceptable"
        elif seconds < 5.0:
            return "slow"
        else:
            return "very_slow"

    def is_performance_concerning(self) -> bool:
        """Check if performance indicates potential issues."""
        category = self.get_validation_performance_category()
        return category in ["slow", "very_slow"]

    # === Missing Tools Analysis ===

    def get_missing_tools_by_criticality(self) -> Dict[str, List[ModelMissingTool]]:
        """Group missing tools by criticality level."""
        grouped = {}
        for criticality in ToolCriticality:
            grouped[criticality.value] = [
                tool for tool in self.missing_tools if tool.criticality == criticality
            ]
        return grouped

    def get_critical_missing_tools(self) -> List[ModelMissingTool]:
        """Get list of critical missing tools."""
        return [tool for tool in self.missing_tools if tool.is_critical_tool()]

    def get_high_priority_missing_tools(self) -> List[ModelMissingTool]:
        """Get list of high priority missing tools."""
        return [tool for tool in self.missing_tools if tool.is_high_priority_tool()]

    def get_missing_tools_by_category(self) -> Dict[str, List[ModelMissingTool]]:
        """Group missing tools by category."""
        from omnibase_core.model.core.model_missing_tool import ToolCategory

        grouped = {}
        for category in ToolCategory:
            grouped[category.value] = [
                tool for tool in self.missing_tools if tool.tool_category == category
            ]
        return grouped

    def get_most_impactful_missing_tool(self) -> Optional[ModelMissingTool]:
        """Get the missing tool with highest business impact."""
        if not self.missing_tools:
            return None

        return max(
            self.missing_tools, key=lambda tool: tool.calculate_business_impact_score()
        )

    # === Severity and Risk Assessment ===

    def _calculate_severity_level(self) -> ValidationSeverity:
        """Calculate overall severity level."""
        if not self.is_valid:
            # Check for critical missing tools
            if any(tool.is_critical_tool() for tool in self.missing_tools):
                return ValidationSeverity.CRITICAL

            # Check for high priority tools
            if any(tool.is_high_priority_tool() for tool in self.missing_tools):
                return ValidationSeverity.HIGH

            # Check missing tools count vs required
            if self.required_tools_count > 0:
                missing_ratio = (
                    self.get_missing_tools_count() / self.required_tools_count
                )
                if missing_ratio > 0.5:
                    return ValidationSeverity.HIGH
                elif missing_ratio > 0.2:
                    return ValidationSeverity.MEDIUM
                else:
                    return ValidationSeverity.LOW

        # Valid but with warnings
        if self.has_warnings():
            return ValidationSeverity.LOW

        return ValidationSeverity.INFO

    def assess_business_risk(self) -> ModelRegistryBusinessRisk:
        """Assess business risk from validation results."""
        return ModelRegistryBusinessRisk(
            overall_risk_level=self._calculate_overall_risk(),
            operational_impact=self._assess_operational_impact(),
            security_risk=self._assess_security_risk(),
            compliance_risk=self._assess_compliance_risk(),
            performance_risk=self._assess_performance_risk(),
            business_continuity_risk=self._assess_business_continuity_risk(),
        )

    def _calculate_overall_risk(self) -> str:
        """Calculate overall business risk level."""
        if self.has_critical_issues():
            return "HIGH"
        elif self.severity_level == ValidationSeverity.HIGH:
            return "MEDIUM"
        elif self.severity_level == ValidationSeverity.MEDIUM:
            return "LOW"
        else:
            return "MINIMAL"

    def _assess_operational_impact(self) -> str:
        """Assess operational impact."""
        if not self.is_valid:
            success_rate = self.get_success_rate()
            if success_rate < 0.5:
                return "SEVERE"
            elif success_rate < 0.8:
                return "MODERATE"
            else:
                return "MINOR"
        return "NONE"

    def _assess_security_risk(self) -> str:
        """Assess security risk from missing tools."""
        from omnibase_core.model.core.model_missing_tool import ToolCategory

        security_tools_missing = any(
            tool.tool_category == ToolCategory.SECURITY for tool in self.missing_tools
        )

        if security_tools_missing:
            return "HIGH"
        elif not self.is_valid:
            return "MEDIUM"
        else:
            return "LOW"

    def _assess_compliance_risk(self) -> str:
        """Assess compliance risk."""
        if self.compliance_score is not None:
            if self.compliance_score < 0.7:
                return "HIGH"
            elif self.compliance_score < 0.9:
                return "MEDIUM"
            else:
                return "LOW"

        # Fallback based on validation status
        if self.has_critical_issues():
            return "HIGH"
        elif not self.is_valid:
            return "MEDIUM"
        else:
            return "LOW"

    def _assess_performance_risk(self) -> str:
        """Assess performance risk."""
        if self.is_performance_concerning():
            return "MEDIUM"
        elif not self.is_valid:
            return "LOW"
        else:
            return "MINIMAL"

    def _assess_business_continuity_risk(self) -> str:
        """Assess business continuity risk."""
        critical_missing = len(self.get_critical_missing_tools())

        if critical_missing > 0:
            return "HIGH"
        elif self.get_missing_tools_count() > self.required_tools_count * 0.3:
            return "MEDIUM"
        elif not self.is_valid:
            return "LOW"
        else:
            return "MINIMAL"

    # === Recovery and Recommendations ===

    def get_recovery_action_plan(self) -> List[ModelRegistryRecoveryAction]:
        """Get prioritized recovery action plan."""
        actions = []

        # Critical tools first
        critical_tools = self.get_critical_missing_tools()
        for tool in critical_tools:
            actions.append(
                ModelRegistryRecoveryAction(
                    priority=1,
                    action_type="fix_critical_tool",
                    tool_name=tool.tool_name,
                    description=f"Fix critical missing tool: {tool.tool_name}",
                    estimated_time=tool.analyze_error_category()["estimated_fix_time"],
                    recommendations=tool.get_recovery_recommendations()[:2],
                )
            )

        # High priority tools
        high_priority_tools = [
            t
            for t in self.get_high_priority_missing_tools()
            if not t.is_critical_tool()
        ]
        for tool in high_priority_tools:
            actions.append(
                ModelRegistryRecoveryAction(
                    priority=2,
                    action_type="fix_high_priority_tool",
                    tool_name=tool.tool_name,
                    description=f"Fix high priority missing tool: {tool.tool_name}",
                    estimated_time=tool.analyze_error_category()["estimated_fix_time"],
                    recommendations=tool.get_recovery_recommendations()[:1],
                )
            )

        # Address warnings if any
        if self.warnings:
            actions.append(
                ModelRegistryRecoveryAction(
                    priority=3,
                    action_type="address_warnings",
                    description=f"Address {len(self.warnings)} validation warnings",
                    estimated_time="30-60 minutes",
                    warnings=self.warnings,
                )
            )

        return sorted(actions, key=lambda x: x.priority)

    def get_comprehensive_recommendations(self) -> List[str]:
        """Get comprehensive recommendations for improving the registry."""
        recommendations = list(self.recommendations) if self.recommendations else []

        # Add automatic recommendations based on analysis
        if self.has_critical_issues():
            recommendations.insert(
                0, "URGENT: Address critical missing tools immediately"
            )

        if self.get_success_rate() < 0.8:
            recommendations.append(
                "Implement missing tools to improve registry completeness"
            )

        if self.is_performance_concerning():
            recommendations.append(
                "Optimize validation performance - current duration is concerning"
            )

        # Add tool-specific recommendations
        for tool in self.missing_tools[:3]:  # Top 3 missing tools
            tool_recs = tool.get_recovery_recommendations()
            if tool_recs:
                recommendations.append(f"{tool.tool_name}: {tool_recs[0]}")

        return recommendations

    # === Business Intelligence ===

    def calculate_compliance_score(self) -> float:
        """Calculate compliance score based on validation results."""
        if self.compliance_score is not None:
            return self.compliance_score

        base_score = self.get_success_rate()  # 0.0 to 1.0

        # Penalize for critical issues
        if self.has_critical_issues():
            base_score *= 0.5

        # Penalize for high severity
        if self.severity_level == ValidationSeverity.HIGH:
            base_score *= 0.7
        elif self.severity_level == ValidationSeverity.MEDIUM:
            base_score *= 0.85

        # Penalize for warnings
        if self.warnings:
            warning_penalty = min(len(self.warnings) * 0.05, 0.2)
            base_score *= 1.0 - warning_penalty

        return max(0.0, min(1.0, base_score))

    def get_operational_health_score(self) -> float:
        """Get overall operational health score (0.0 to 1.0)."""
        # Base score from validation success
        health_score = 1.0 if self.is_successful() else 0.0

        # Factor in completion percentage
        completion_factor = self.get_success_rate()
        health_score = (health_score * 0.4) + (completion_factor * 0.6)

        # Penalize for critical issues
        if self.has_critical_issues():
            health_score *= 0.3
        elif self.severity_level == ValidationSeverity.HIGH:
            health_score *= 0.6
        elif self.severity_level == ValidationSeverity.MEDIUM:
            health_score *= 0.8

        return max(0.0, min(1.0, health_score))

    def assess_business_impact(self) -> ModelRegistryBusinessImpact:
        """Comprehensive business impact assessment."""
        business_risk = self.assess_business_risk()

        return ModelRegistryBusinessImpact(
            operational_health_score=self.get_operational_health_score(),
            compliance_score=self.calculate_compliance_score(),
            success_rate_percentage=self.get_completion_percentage(),
            critical_tools_missing=len(self.get_critical_missing_tools()),
            high_priority_tools_missing=len(self.get_high_priority_missing_tools()),
            estimated_fix_effort=self._estimate_total_fix_effort(),
            user_experience_impact=self._assess_user_experience_impact(),
            system_reliability_impact=self._assess_reliability_impact(),
            # Business risk components from the risk assessment
            overall_risk_level=business_risk.overall_risk_level,
            operational_impact=business_risk.operational_impact,
            security_risk=business_risk.security_risk,
            compliance_risk=business_risk.compliance_risk,
            performance_risk=business_risk.performance_risk,
            business_continuity_risk=business_risk.business_continuity_risk,
        )

    def _estimate_total_fix_effort(self) -> str:
        """Estimate total effort to fix all issues."""
        if not self.missing_tools:
            return "No effort required"

        total_hours = 0
        for tool in self.missing_tools:
            time_estimate = tool.analyze_error_category()["estimated_fix_time"]
            # Parse time estimates (rough approximation)
            if "15-30 minutes" in time_estimate:
                total_hours += 0.375
            elif "30-60 minutes" in time_estimate:
                total_hours += 0.75
            elif "1-2 hours" in time_estimate:
                total_hours += 1.5
            elif "1-4 hours" in time_estimate:
                total_hours += 2.5
            elif "2-6 hours" in time_estimate:
                total_hours += 4
            elif "4-8 hours" in time_estimate:
                total_hours += 6
            elif "8-16 hours" in time_estimate:
                total_hours += 12
            else:
                total_hours += 2  # Default estimate

        if total_hours < 1:
            return "Less than 1 hour"
        elif total_hours < 8:
            return f"Approximately {total_hours:.1f} hours"
        elif total_hours < 40:
            return f"Approximately {total_hours/8:.1f} days"
        else:
            return f"Approximately {total_hours/40:.1f} weeks"

    def _assess_user_experience_impact(self) -> str:
        """Assess impact on user experience."""
        if self.has_critical_issues():
            return "Severe degradation expected"
        elif not self.is_valid:
            success_rate = self.get_success_rate()
            if success_rate < 0.5:
                return "Major functionality unavailable"
            elif success_rate < 0.8:
                return "Some features may not work"
            else:
                return "Minor impact on user experience"
        else:
            return "No impact on user experience"

    def _assess_reliability_impact(self) -> str:
        """Assess impact on system reliability."""
        if self.has_critical_issues():
            return "System stability at risk"
        elif self.severity_level == ValidationSeverity.HIGH:
            return "Reduced system reliability"
        elif not self.is_valid:
            return "Some reliability concerns"
        else:
            return "No reliability impact"

    # === Monitoring Integration ===

    def get_monitoring_metrics(self) -> "ModelMonitoringMetrics":
        """Get comprehensive metrics for monitoring systems."""
        from omnibase_core.model.core.model_monitoring_metrics import (
            MetricValue, ModelMonitoringMetrics)

        custom_metrics = {
            "validation_id": MetricValue(
                value=(
                    self.metadata.get("validation_id", "unknown")
                    if self.metadata
                    else "unknown"
                )
            ),
            "node_class_name": MetricValue(value=self.node_class_name),
            "is_valid": MetricValue(value=self.is_valid),
            "validation_status": MetricValue(
                value=(
                    self.validation_status.value
                    if self.validation_status
                    else "unknown"
                )
            ),
            "severity_level": MetricValue(
                value=self.severity_level.value if self.severity_level else "unknown"
            ),
            "success_rate": MetricValue(value=self.get_success_rate()),
            "completion_percentage": MetricValue(
                value=self.get_completion_percentage()
            ),
            "required_tools_count": MetricValue(value=self.required_tools_count),
            "missing_tools_count": MetricValue(value=self.get_missing_tools_count()),
            "critical_tools_missing": MetricValue(
                value=len(self.get_critical_missing_tools())
            ),
            "high_priority_tools_missing": MetricValue(
                value=len(self.get_high_priority_missing_tools())
            ),
            "warnings_count": MetricValue(
                value=len(self.warnings) if self.warnings else 0
            ),
            "has_critical_issues": MetricValue(value=self.has_critical_issues()),
            "performance_category": MetricValue(
                value=self.get_validation_performance_category()
            ),
        }

        return ModelMonitoringMetrics(
            response_time_ms=(
                float(self.validation_duration_ms)
                if self.validation_duration_ms
                else None
            ),
            success_rate=self.get_success_rate() * 100.0,
            compliance_score=self.calculate_compliance_score() * 100.0,
            health_score=self.get_operational_health_score() * 100.0,
            custom_metrics=custom_metrics,
        )

    def get_audit_trail(self) -> List["ModelAuditEntry"]:
        """Get comprehensive audit trail for compliance and debugging."""
        from omnibase_core.model.core.model_audit_entry import ModelAuditEntry

        audit_entries = []

        # Add validation start event
        if self.validation_start_time:
            audit_entries.append(
                ModelAuditEntry(
                    timestamp=self.validation_start_time,
                    action="validation_started",
                    actor="system",
                    resource=f"registry_validation_{self.node_class_name}",
                    result="initiated",
                    details={
                        "node_class_name": self.node_class_name,
                        "required_tools_count": self.required_tools_count,
                        "validation_types": (
                            [vt.value for vt in self.validation_types]
                            if self.validation_types
                            else []
                        ),
                    },
                )
            )

        # Add missing tools discovery
        for tool in self.missing_tools[:5]:  # Limit to first 5 for brevity
            audit_entries.append(
                ModelAuditEntry(
                    timestamp=self.validation_start_time or datetime.now().isoformat(),
                    action="missing_tool_detected",
                    actor="system",
                    resource=f"tool_{tool.tool_name}",
                    result="missing",
                    details={
                        "criticality": tool.criticality.value,
                        "error_message": tool.error_message,
                        "recovery_recommendations": tool.get_recovery_recommendations()[
                            :2
                        ],
                    },
                )
            )

        # Add warnings as audit events
        for warning in (self.warnings or [])[:5]:  # Limit to first 5
            audit_entries.append(
                ModelAuditEntry(
                    timestamp=self.validation_start_time or datetime.now().isoformat(),
                    action="validation_warning",
                    actor="system",
                    resource=f"registry_validation_{self.node_class_name}",
                    result="warning",
                    details={"warning": warning},
                )
            )

        # Add validation completion event
        if self.validation_end_time:
            audit_entries.append(
                ModelAuditEntry(
                    timestamp=self.validation_end_time,
                    action="validation_completed",
                    actor="system",
                    resource=f"registry_validation_{self.node_class_name}",
                    result=(
                        self.validation_status.value
                        if self.validation_status
                        else "unknown"
                    ),
                    details={
                        "is_valid": self.is_valid,
                        "severity_level": (
                            self.severity_level.value
                            if self.severity_level
                            else "unknown"
                        ),
                        "duration_ms": self.validation_duration_ms,
                        "success_rate": self.get_success_rate(),
                        "missing_tools_count": self.get_missing_tools_count(),
                        "warnings_count": len(self.warnings) if self.warnings else 0,
                        "compliance_score": self.calculate_compliance_score(),
                        "operational_health_score": self.get_operational_health_score(),
                    },
                )
            )

        return audit_entries

    # === Factory Methods ===

    @classmethod
    def create_success(
        cls,
        node_class_name: str,
        required_tools_count: int,
        duration_ms: Optional[int] = None,
    ) -> "ModelRegistryValidationResult":
        """Create a successful validation result."""
        return cls(
            is_valid=True,
            node_class_name=node_class_name,
            required_tools_count=required_tools_count,
            available_tools_count=required_tools_count,
            validation_status=ValidationStatus.VALID,
            validation_duration_ms=duration_ms,
            severity_level=ValidationSeverity.INFO,
            validation_start_time=datetime.now().isoformat(),
            validation_end_time=datetime.now().isoformat(),
        )

    @classmethod
    def create_failure(
        cls,
        node_class_name: str,
        required_tools_count: int,
        missing_tools: List[ModelMissingTool],
        error_message: str,
        duration_ms: Optional[int] = None,
    ) -> "ModelRegistryValidationResult":
        """Create a failed validation result."""
        return cls(
            is_valid=False,
            node_class_name=node_class_name,
            required_tools_count=required_tools_count,
            missing_tools=missing_tools,
            error_message=error_message,
            available_tools_count=required_tools_count - len(missing_tools),
            validation_status=ValidationStatus.INVALID,
            validation_duration_ms=duration_ms,
            validation_start_time=datetime.now().isoformat(),
            validation_end_time=datetime.now().isoformat(),
        )

    @classmethod
    def create_partial(
        cls,
        node_class_name: str,
        required_tools_count: int,
        missing_tools: List[ModelMissingTool],
        warnings: List[str],
        duration_ms: Optional[int] = None,
    ) -> "ModelRegistryValidationResult":
        """Create a partial validation result."""
        return cls(
            is_valid=True,  # Still valid but with warnings
            node_class_name=node_class_name,
            required_tools_count=required_tools_count,
            missing_tools=missing_tools,
            available_tools_count=required_tools_count - len(missing_tools),
            warnings=warnings,
            validation_status=ValidationStatus.PARTIAL,
            validation_duration_ms=duration_ms,
            validation_start_time=datetime.now().isoformat(),
            validation_end_time=datetime.now().isoformat(),
        )

    @classmethod
    def create_error(
        cls, node_class_name: str, error_message: str, duration_ms: Optional[int] = None
    ) -> "ModelRegistryValidationResult":
        """Create an error validation result."""
        return cls(
            is_valid=False,
            node_class_name=node_class_name,
            required_tools_count=0,
            error_message=error_message,
            validation_status=ValidationStatus.ERROR,
            severity_level=ValidationSeverity.CRITICAL,
            validation_duration_ms=duration_ms,
            validation_start_time=datetime.now().isoformat(),
            validation_end_time=datetime.now().isoformat(),
        )
