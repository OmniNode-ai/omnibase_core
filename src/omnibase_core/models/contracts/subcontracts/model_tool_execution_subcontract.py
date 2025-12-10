"""
Tool Execution Subcontract Model.



Dedicated subcontract model for tool execution functionality providing:
- Tool execution enabling/disabling
- Execution timeout configuration
- Parallel execution limits
- Retry on failure
- Output capture and environment variable management
- Event-driven execution request handling

This model is composed into node contracts that require tool execution capabilities,
providing clean separation between node logic and tool execution behavior.

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelToolExecutionSubcontract(BaseModel):
    """
    Tool Execution subcontract model for standardized tool execution.

    Comprehensive tool execution configuration providing timeout management,
    parallel execution limits, retry behavior, output capture, and environment
    variable management for ONEX tool nodes.

    This subcontract enables tool nodes to:
    - Enable/disable tool execution dynamically
    - Configure execution timeouts per tool invocation
    - Limit concurrent tool executions to prevent resource exhaustion
    - Retry failed tool executions with configurable behavior
    - Capture stdout/stderr output from tool executions
    - Manage environment variables for tool processes
    - Handle tool execution request events via MixinToolExecution

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    # Core execution configuration
    enabled: bool = Field(
        default=True,
        description="Whether tool execution is enabled for this node",
    )

    timeout_seconds: float = Field(
        default=30.0,
        ge=0.1,
        le=3600.0,
        description="Maximum execution time per tool invocation in seconds",
    )

    # Parallel execution limits
    max_parallel_executions: int = Field(
        default=1,
        ge=1,
        le=100,
        description="Maximum number of concurrent tool executions allowed",
    )

    queue_overflow_policy: str = Field(
        default="block",
        description="Policy when parallel execution limit reached: block, reject, or drop_oldest",
    )

    max_queue_size: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum size of execution queue when overflow policy is 'block'",
    )

    # Retry configuration
    retry_on_failure: bool = Field(
        default=False,
        description="Whether to automatically retry failed tool executions",
    )

    max_retry_attempts: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts for failed executions",
    )

    retry_delay_seconds: float = Field(
        default=1.0,
        ge=0.0,
        le=60.0,
        description="Delay between retry attempts in seconds",
    )

    retry_exponential_backoff: bool = Field(
        default=True,
        description="Whether to use exponential backoff for retry delays",
    )

    # Output capture configuration
    capture_output: bool = Field(
        default=True,
        description="Whether to capture stdout and stderr from tool executions",
    )

    output_buffer_size_kb: int = Field(
        default=1024,
        ge=1,
        le=102400,
        description="Maximum size of output buffer in kilobytes (1KB-100MB)",
    )

    truncate_output_on_overflow: bool = Field(
        default=True,
        description="Whether to truncate output when buffer size is exceeded",
    )

    stream_output_to_log: bool = Field(
        default=False,
        description="Whether to stream output to logs in real-time",
    )

    # Environment variable management
    environment_variables: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to set for tool executions",
    )

    inherit_parent_environment: bool = Field(
        default=True,
        description="Whether to inherit environment variables from parent process",
    )

    sanitize_environment: bool = Field(
        default=True,
        description="Whether to sanitize environment variables for security",
    )

    # Event-driven execution
    enable_event_execution: bool = Field(
        default=True,
        description="Whether to enable event-driven tool execution via MixinToolExecution",
    )

    execution_request_event_pattern: str = Field(
        default="tool.execution.request",
        description="Event pattern to listen for execution requests",
    )

    publish_execution_responses: bool = Field(
        default=True,
        description="Whether to publish execution response events",
    )

    # Resource management
    resource_isolation: bool = Field(
        default=False,
        description="Whether to isolate tool executions in separate processes/containers",
    )

    max_memory_mb: int | None = Field(
        default=None,
        ge=1,
        le=102400,
        description="Maximum memory limit for tool execution in MB (None = no limit)",
    )

    max_cpu_percent: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Maximum CPU usage percent for tool execution (None = no limit)",
    )

    # Error handling
    fail_fast: bool = Field(
        default=True,
        description="Whether to fail immediately on first error or continue execution",
    )

    error_handling_strategy: str = Field(
        default="propagate",
        description="Error handling strategy: propagate, suppress, or log_and_continue",
    )

    preserve_error_context: bool = Field(
        default=True,
        description="Whether to preserve full error context and stack traces",
    )

    # Monitoring and observability
    emit_execution_metrics: bool = Field(
        default=True,
        description="Whether to emit metrics for tool execution performance",
    )

    execution_tracing_enabled: bool = Field(
        default=False,
        description="Whether to enable detailed execution tracing",
    )

    log_execution_start_end: bool = Field(
        default=True,
        description="Whether to log execution start and end events",
    )

    @model_validator(mode="after")
    def validate_overflow_policy(self) -> Self:
        """Validate queue_overflow_policy is one of allowed values."""
        allowed_policies = ["block", "reject", "drop_oldest"]
        if self.queue_overflow_policy not in allowed_policies:
            msg = f"queue_overflow_policy must be one of {allowed_policies}, got '{self.queue_overflow_policy}'"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("queue_overflow_policy"),
                        "allowed_values": ModelSchemaValue.from_value(allowed_policies),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_error_handling_strategy(self) -> Self:
        """Validate error_handling_strategy is one of allowed values."""
        allowed_strategies = ["propagate", "suppress", "log_and_continue"]
        if self.error_handling_strategy not in allowed_strategies:
            msg = f"error_handling_strategy must be one of {allowed_strategies}, got '{self.error_handling_strategy}'"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("error_handling_strategy"),
                        "allowed_values": ModelSchemaValue.from_value(
                            allowed_strategies
                        ),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_retry_configuration(self) -> Self:
        """Validate retry configuration is consistent."""
        if self.retry_on_failure and self.max_retry_attempts < 1:
            msg = (
                "max_retry_attempts must be at least 1 when retry_on_failure is enabled"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("max_retry_attempts"),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_resource_limits(self) -> Self:
        """Validate resource limits are consistent with isolation settings."""
        if not self.resource_isolation:
            if self.max_memory_mb is not None or self.max_cpu_percent is not None:
                msg = "Resource limits (max_memory_mb, max_cpu_percent) require resource_isolation=True"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                            "field": ModelSchemaValue.from_value("resource_isolation"),
                        },
                    ),
                )
        return self

    @model_validator(mode="after")
    def validate_event_execution_configuration(self) -> Self:
        """Validate event-driven execution configuration is consistent."""
        if self.enable_event_execution and not self.enabled:
            msg = "enable_event_execution=True requires enabled=True"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "field": ModelSchemaValue.from_value("enable_event_execution"),
                    },
                ),
            )
        return self

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,  # Validate on attribute assignment
    )

    def get_effective_timeout(self, attempt: int = 0) -> float:
        """
        Get the effective timeout for a given retry attempt.

        Args:
            attempt: Current retry attempt number (0 = first attempt)

        Returns:
            Effective timeout in seconds
        """
        if not self.retry_on_failure or not self.retry_exponential_backoff:
            return self.timeout_seconds

        # Apply exponential backoff to timeout if enabled
        multiplier = 1.5**attempt
        return min(self.timeout_seconds * multiplier, self.timeout_seconds * 3)

    def get_retry_delay(self, attempt: int) -> float:
        """
        Get the delay before the next retry attempt.

        Args:
            attempt: Current retry attempt number (1 = first retry)

        Returns:
            Delay in seconds before next retry
        """
        if not self.retry_exponential_backoff:
            return self.retry_delay_seconds

        # Exponential backoff: delay * (2 ^ (attempt - 1))
        multiplier: int = 2 ** (attempt - 1)
        delay: float = self.retry_delay_seconds * multiplier
        return min(delay, 60.0)

    def should_retry(self, attempt: int, error: Exception | None = None) -> bool:
        """
        Determine if execution should be retried.

        Args:
            attempt: Current attempt number (1 = first attempt, 2 = first retry)
            error: Exception that occurred (optional)

        Returns:
            True if execution should be retried
        """
        if not self.retry_on_failure:
            return False

        if attempt > self.max_retry_attempts:
            return False

        # Additional logic could check error type here
        return True

    def get_output_buffer_size_bytes(self) -> int:
        """
        Get the output buffer size in bytes.

        Returns:
            Buffer size in bytes
        """
        return self.output_buffer_size_kb * 1024

    def get_effective_environment(
        self, additional_vars: dict[str, str] | None = None
    ) -> dict[str, str]:
        """
        Get the effective environment variables for tool execution.

        Args:
            additional_vars: Additional environment variables to merge

        Returns:
            Merged environment variables
        """
        import os

        env: dict[str, str] = {}

        # Start with parent environment if inheritance is enabled
        if self.inherit_parent_environment:
            env.update(os.environ)

        # Add configured environment variables
        env.update(self.environment_variables)

        # Add additional variables
        if additional_vars:
            env.update(additional_vars)

        # Sanitize if enabled
        if self.sanitize_environment:
            # Remove potentially dangerous variables
            dangerous_vars = [
                "LD_PRELOAD",
                "LD_LIBRARY_PATH",
                "DYLD_INSERT_LIBRARIES",
                "DYLD_LIBRARY_PATH",
            ]
            for var in dangerous_vars:
                env.pop(var, None)

        return env

    def is_within_resource_limits(
        self, memory_mb: float | None = None, cpu_percent: float | None = None
    ) -> bool:
        """
        Check if current resource usage is within configured limits.

        Args:
            memory_mb: Current memory usage in MB
            cpu_percent: Current CPU usage percent

        Returns:
            True if within limits or no limits configured
        """
        if not self.resource_isolation:
            return True

        if self.max_memory_mb is not None and memory_mb is not None:
            if memory_mb > self.max_memory_mb:
                return False

        if self.max_cpu_percent is not None and cpu_percent is not None:
            if cpu_percent > self.max_cpu_percent:
                return False

        return True
