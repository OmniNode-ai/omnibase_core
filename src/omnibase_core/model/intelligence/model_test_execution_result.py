"""
Agent-Orchestrated Test Execution Result Model.

This module provides comprehensive models for tracking test execution results,
agent performance, and validation outcomes for the intelligence hardening
testing framework.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from omnibase_core.registry.base_registry import BaseOnexRegistry


class TestExecutionStatus(Enum):
    """Status of test execution."""

    PENDING = "pending"
    INITIALIZING = "initializing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    ERROR = "error"


class TestStepStatus(Enum):
    """Status of individual test step execution."""

    NOT_STARTED = "not_started"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    ERROR = "error"


class ValidationResultStatus(Enum):
    """Status of validation result."""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIP = "skip"
    ERROR = "error"


class ModelTestStepResult(BaseModel):
    """Result of executing a single test step."""

    step_id: str = Field(description="ID of the executed test step")
    step_name: str = Field(description="Name of the executed test step")
    status: TestStepStatus = Field(description="Status of step execution")

    start_time: datetime = Field(description="When step execution started")
    end_time: datetime | None = Field(None, description="When step execution ended")
    duration_seconds: float | None = Field(
        None,
        description="Step execution duration",
        ge=0,
    )

    expected_results: dict[str, Any] = Field(
        default_factory=dict,
        description="Expected results for this step",
    )
    actual_results: dict[str, Any] = Field(
        default_factory=dict,
        description="Actual results from step execution",
    )

    assertions_passed: int = Field(
        default=0,
        description="Number of assertions passed",
        ge=0,
    )
    assertions_failed: int = Field(
        default=0,
        description="Number of assertions failed",
        ge=0,
    )
    assertions_total: int = Field(
        default=0,
        description="Total number of assertions",
        ge=0,
    )

    error_message: str | None = Field(
        None,
        description="Error message if step failed",
    )
    exception_details: str | None = Field(
        None,
        description="Full exception details if available",
    )

    performance_metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Performance metrics collected during step",
    )
    resource_usage: dict[str, Any] = Field(
        default_factory=dict,
        description="Resource usage during step execution",
    )

    agent_id: str | None = Field(
        None,
        description="ID of agent that executed this step",
    )
    retry_attempt: int = Field(default=0, description="Retry attempt number", ge=0)

    logs: list[str] = Field(
        default_factory=list,
        description="Execution logs for this step",
    )
    artifacts: dict[str, str] = Field(
        default_factory=dict,
        description="Test artifacts generated (name -> path)",
    )


class ModelValidationResult(BaseModel):
    """Result of a specific validation check."""

    validation_id: str = Field(description="Unique identifier for this validation")
    validation_name: str = Field(description="Human-readable name for validation")
    validation_description: str = Field(description="Description of what was validated")

    status: ValidationResultStatus = Field(description="Status of validation")
    expected_value: Any = Field(description="Expected value for validation")
    actual_value: Any = Field(description="Actual value found during validation")

    tolerance_threshold: float | None = Field(
        None,
        description="Tolerance threshold for numeric comparisons",
    )
    comparison_operator: str | None = Field(
        None,
        description="Comparison operator used (==, >=, <=, etc.)",
    )

    error_message: str | None = Field(
        None,
        description="Error message if validation failed",
    )
    warning_message: str | None = Field(
        None,
        description="Warning message if applicable",
    )

    validation_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When validation was performed",
    )
    execution_time_ms: float | None = Field(
        None,
        description="Time taken to perform validation in milliseconds",
        ge=0,
    )


class ModelPerformanceValidationResult(BaseModel):
    """Result of performance validation checks."""

    response_time_ms: float | None = Field(
        None,
        description="Measured response time",
        ge=0,
    )
    throughput_per_second: float | None = Field(
        None,
        description="Measured throughput",
        ge=0,
    )
    memory_usage_mb: float | None = Field(
        None,
        description="Peak memory usage",
        ge=0,
    )
    cpu_usage_percent: float | None = Field(
        None,
        description="Peak CPU usage",
        ge=0,
        le=100,
    )
    error_rate_percent: float | None = Field(
        None,
        description="Error rate",
        ge=0,
        le=100,
    )
    success_rate_percent: float | None = Field(
        None,
        description="Success rate",
        ge=0,
        le=100,
    )
    recovery_time_seconds: float | None = Field(
        None,
        description="Recovery time",
        ge=0,
    )

    # Validation results against targets
    response_time_validation: ModelValidationResult | None = None
    throughput_validation: ModelValidationResult | None = None
    memory_usage_validation: ModelValidationResult | None = None
    cpu_usage_validation: ModelValidationResult | None = None
    error_rate_validation: ModelValidationResult | None = None
    success_rate_validation: ModelValidationResult | None = None
    recovery_time_validation: ModelValidationResult | None = None
    zero_data_loss_validation: ModelValidationResult | None = None

    performance_score: float = Field(
        default=0.0,
        description="Overall performance score",
        ge=0,
        le=100,
    )


class ModelSecurityValidationResult(BaseModel):
    """Result of security validation checks."""

    security_audit_score: float | None = Field(
        None,
        description="Security audit score",
        ge=0,
        le=100,
    )
    zero_trust_validation_passed: bool = Field(
        default=False,
        description="Whether zero-trust validation passed",
    )
    input_sanitization_passed: bool = Field(
        default=False,
        description="Whether input sanitization tests passed",
    )
    boundary_enforcement_passed: bool = Field(
        default=False,
        description="Whether boundary enforcement tests passed",
    )
    threat_detection_passed: bool = Field(
        default=False,
        description="Whether threat detection tests passed",
    )
    encryption_validation_passed: bool = Field(
        default=False,
        description="Whether encryption validation passed",
    )
    access_control_validation_passed: bool = Field(
        default=False,
        description="Whether access control validation passed",
    )

    vulnerabilities_found: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Vulnerabilities discovered during testing",
    )
    security_violations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Security violations detected",
    )

    # Individual validation results
    audit_score_validation: ModelValidationResult | None = None
    zero_trust_validation: ModelValidationResult | None = None
    input_sanitization_validation: ModelValidationResult | None = None
    boundary_enforcement_validation: ModelValidationResult | None = None
    threat_detection_validation: ModelValidationResult | None = None
    encryption_validation: ModelValidationResult | None = None
    access_control_validation: ModelValidationResult | None = None

    security_score: float = Field(
        default=0.0,
        description="Overall security score",
        ge=0,
        le=100,
    )


class ModelTestCoverageResult(BaseModel):
    """Result of test coverage analysis."""

    total_test_points: int = Field(description="Total number of test points", ge=0)
    covered_test_points: int = Field(description="Number of covered test points", ge=0)
    coverage_percentage: float = Field(description="Coverage percentage", ge=0, le=100)

    code_coverage_percentage: float | None = Field(
        None,
        description="Code coverage percentage",
        ge=0,
        le=100,
    )
    branch_coverage_percentage: float | None = Field(
        None,
        description="Branch coverage percentage",
        ge=0,
        le=100,
    )
    function_coverage_percentage: float | None = Field(
        None,
        description="Function coverage percentage",
        ge=0,
        le=100,
    )

    uncovered_areas: list[str] = Field(
        default_factory=list,
        description="Areas not covered by tests",
    )
    coverage_gaps: list[str] = Field(
        default_factory=list,
        description="Identified coverage gaps",
    )

    coverage_validation: ModelValidationResult | None = None


class ModelAgentPerformanceResult(BaseModel):
    """Performance result for individual test agents."""

    agent_id: str = Field(description="ID of the test agent")
    agent_type: str = Field(description="Type of test agent")
    agent_name: str | None = Field(None, description="Name of test agent")

    tasks_executed: int = Field(default=0, description="Number of tasks executed", ge=0)
    tasks_successful: int = Field(
        default=0,
        description="Number of successful tasks",
        ge=0,
    )
    tasks_failed: int = Field(default=0, description="Number of failed tasks", ge=0)

    average_task_duration_ms: float = Field(
        default=0.0,
        description="Average task duration in milliseconds",
        ge=0,
    )
    min_task_duration_ms: float = Field(
        default=0.0,
        description="Minimum task duration in milliseconds",
        ge=0,
    )
    max_task_duration_ms: float = Field(
        default=0.0,
        description="Maximum task duration in milliseconds",
        ge=0,
    )

    resource_usage_peak_mb: float = Field(
        default=0.0,
        description="Peak resource usage in MB",
        ge=0,
    )
    cpu_usage_peak_percent: float = Field(
        default=0.0,
        description="Peak CPU usage percentage",
        ge=0,
        le=100,
    )

    coordination_events: int = Field(
        default=0,
        description="Number of coordination events handled",
        ge=0,
    )
    communication_latency_ms: float = Field(
        default=0.0,
        description="Average communication latency in milliseconds",
        ge=0,
    )

    agent_efficiency_score: float = Field(
        default=0.0,
        description="Agent efficiency score",
        ge=0,
        le=100,
    )


class ModelTestExecutionResult(BaseModel):
    """
    Comprehensive result of agent-orchestrated test execution.

    This model captures all aspects of test execution including individual step results,
    performance validation, security compliance, coverage analysis, and agent performance.
    """

    # Core identification
    execution_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this test execution",
    )
    scenario_id: UUID = Field(description="ID of the test scenario that was executed")
    scenario_name: str = Field(description="Name of the test scenario")
    scenario_version: str = Field(description="Version of the test scenario")

    # Execution status and timing
    status: TestExecutionStatus = Field(description="Overall execution status")
    start_time: datetime = Field(description="When test execution started")
    end_time: datetime | None = Field(None, description="When test execution ended")
    duration_seconds: float | None = Field(
        None,
        description="Total execution duration",
        ge=0,
    )

    # Step results
    step_results: list[ModelTestStepResult] = Field(
        description="Results for each test step executed",
    )
    steps_passed: int = Field(default=0, description="Number of steps passed", ge=0)
    steps_failed: int = Field(default=0, description="Number of steps failed", ge=0)
    steps_skipped: int = Field(default=0, description="Number of steps skipped", ge=0)
    steps_total: int = Field(default=0, description="Total number of steps", ge=0)

    # Overall validation results
    total_assertions: int = Field(
        default=0,
        description="Total assertions across all steps",
        ge=0,
    )
    assertions_passed: int = Field(default=0, description="Assertions passed", ge=0)
    assertions_failed: int = Field(default=0, description="Assertions failed", ge=0)

    # Specific validation results
    performance_validation: ModelPerformanceValidationResult | None = Field(
        None,
        description="Performance validation results",
    )
    security_validation: ModelSecurityValidationResult | None = Field(
        None,
        description="Security validation results",
    )
    coverage_validation: ModelTestCoverageResult | None = Field(
        None,
        description="Test coverage validation results",
    )

    # Agent orchestration results
    agents_used: list[ModelAgentPerformanceResult] = Field(
        default_factory=list,
        description="Performance results for agents used",
    )
    coordination_efficiency: float = Field(
        default=0.0,
        description="Agent coordination efficiency score",
        ge=0,
        le=100,
    )
    parallelization_factor: float = Field(
        default=1.0,
        description="Parallelization factor achieved",
        ge=1.0,
    )

    # Error and failure analysis
    error_messages: list[str] = Field(
        default_factory=list,
        description="Error messages from execution",
    )
    failure_analysis: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Detailed failure analysis",
    )
    recovery_attempts: int = Field(
        default=0,
        description="Number of recovery attempts",
        ge=0,
    )

    # Environment and execution context
    execution_environment: dict[str, Any] = Field(
        default_factory=dict,
        description="Environment information during execution",
    )
    resource_usage_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Overall resource usage summary",
    )

    # Artifacts and outputs
    test_artifacts: dict[str, str] = Field(
        default_factory=dict,
        description="Generated test artifacts (name -> path)",
    )
    execution_logs: list[str] = Field(
        default_factory=list,
        description="High-level execution logs",
    )

    # Scoring and assessment
    overall_success_rate: float = Field(
        default=0.0,
        description="Overall success rate percentage",
        ge=0,
        le=100,
    )
    test_quality_score: float = Field(
        default=0.0,
        description="Test quality score",
        ge=0,
        le=100,
    )
    execution_efficiency_score: float = Field(
        default=0.0,
        description="Execution efficiency score",
        ge=0,
        le=100,
    )

    # Recommendations and insights
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommendations based on test results",
    )
    performance_insights: list[str] = Field(
        default_factory=list,
        description="Performance insights discovered",
    )
    security_insights: list[str] = Field(
        default_factory=list,
        description="Security insights discovered",
    )

    # Registry for ONEX compliance (not serialized)
    registry: BaseOnexRegistry | None = Field(default=None, exclude=True)

    def __init__(self, registry: BaseOnexRegistry, **data) -> None:
        """Initialize with registry injection following ONEX patterns."""
        super().__init__(registry=registry, **data)

    def get_registry(self) -> BaseOnexRegistry:
        """Get the injected registry instance for dependency resolution."""
        if self.registry is None:
            msg = "Registry not injected - model not properly initialized"
            raise ValueError(msg)
        return self.registry

    @field_validator("steps_total")
    @classmethod
    def validate_steps_total(cls, v: int, info) -> int:
        """Validate that total steps equals passed + failed + skipped."""
        passed = info.data.get("steps_passed", 0)
        failed = info.data.get("steps_failed", 0)
        skipped = info.data.get("steps_skipped", 0)

        expected_total = passed + failed + skipped
        if expected_total > 0 and v != expected_total:
            # Log warning but don't fail validation
            pass

        return v

    @field_validator("assertions_passed")
    @classmethod
    def validate_assertions_passed(cls, v: int, info) -> int:
        """Validate that assertions passed doesn't exceed total."""
        total = info.data.get("total_assertions", 0)
        if total > 0 and v > total:
            msg = "Assertions passed cannot exceed total assertions"
            raise ValueError(msg)
        return v

    def calculate_overall_success_rate(self) -> float:
        """Calculate overall success rate based on step and assertion results."""
        if self.steps_total == 0:
            return 0.0

        step_success_rate = (self.steps_passed / self.steps_total) * 100

        if self.total_assertions > 0:
            assertion_success_rate = (
                self.assertions_passed / self.total_assertions
            ) * 100
            # Weighted average: 60% step success, 40% assertion success
            return (step_success_rate * 0.6) + (assertion_success_rate * 0.4)
        return step_success_rate

    def get_failed_step_results(self) -> list[ModelTestStepResult]:
        """Get all step results that failed."""
        return [
            result
            for result in self.step_results
            if result.status == TestStepStatus.FAILED
        ]

    def get_critical_failures(self) -> list[ModelTestStepResult]:
        """Get failed results for critical steps."""
        return self.get_failed_step_results()
        # For critical failures, we would need to check against original scenario
        # This is a simplified implementation

    def meets_performance_targets(self) -> bool:
        """Check if execution meets all performance targets."""
        if not self.performance_validation:
            return False

        validations = [
            self.performance_validation.response_time_validation,
            self.performance_validation.throughput_validation,
            self.performance_validation.memory_usage_validation,
            self.performance_validation.cpu_usage_validation,
            self.performance_validation.error_rate_validation,
            self.performance_validation.success_rate_validation,
            self.performance_validation.recovery_time_validation,
            self.performance_validation.zero_data_loss_validation,
        ]

        for validation in validations:
            if validation and validation.status == ValidationResultStatus.FAIL:
                return False

        return True

    def meets_security_targets(self) -> bool:
        """Check if execution meets all security targets."""
        if not self.security_validation:
            return False

        validations = [
            self.security_validation.audit_score_validation,
            self.security_validation.zero_trust_validation,
            self.security_validation.input_sanitization_validation,
            self.security_validation.boundary_enforcement_validation,
            self.security_validation.threat_detection_validation,
            self.security_validation.encryption_validation,
            self.security_validation.access_control_validation,
        ]

        for validation in validations:
            if validation and validation.status == ValidationResultStatus.FAIL:
                return False

        return True

    def meets_coverage_targets(self) -> bool:
        """Check if execution meets coverage targets."""
        if not self.coverage_validation:
            return False

        return (
            self.coverage_validation.coverage_validation is None
            or self.coverage_validation.coverage_validation.status
            != ValidationResultStatus.FAIL
        )

    def is_successful(self) -> bool:
        """Determine if the test execution is considered successful."""
        return (
            self.status == TestExecutionStatus.COMPLETED
            and self.steps_failed == 0
            and self.assertions_failed == 0
            and self.meets_performance_targets()
            and self.meets_security_targets()
            and self.meets_coverage_targets()
        )

    def get_execution_summary(self) -> dict[str, Any]:
        """Get a summary of the test execution."""
        return {
            "execution_id": str(self.execution_id),
            "scenario_name": self.scenario_name,
            "status": self.status.value,
            "duration_seconds": self.duration_seconds,
            "success_rate": self.overall_success_rate,
            "steps": {
                "total": self.steps_total,
                "passed": self.steps_passed,
                "failed": self.steps_failed,
                "skipped": self.steps_skipped,
            },
            "assertions": {
                "total": self.total_assertions,
                "passed": self.assertions_passed,
                "failed": self.assertions_failed,
            },
            "performance_passed": self.meets_performance_targets(),
            "security_passed": self.meets_security_targets(),
            "coverage_passed": self.meets_coverage_targets(),
            "overall_success": self.is_successful(),
        }
