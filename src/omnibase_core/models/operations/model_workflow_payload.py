"""
Strongly-typed workflow payload structure.

Replaces dict[str, Any] usage in workflow payloads with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_workflow_type import EnumWorkflowType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

# Workflow types - using EnumWorkflowType from enums package


# Structured execution context and configuration types to replace primitive soup patterns (defined first)
class ModelWorkflowExecutionContext(BaseModel):
    """Structured workflow execution context."""

    execution_id: str = Field(
        default="",
        description="Unique workflow execution identifier",
    )
    parent_execution_id: UUID | None = Field(
        default=None,
        description="Parent workflow execution identifier",
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation identifier",
    )
    tenant_id: UUID | None = Field(default=None, description="Tenant identifier")
    user_id: UUID | None = Field(default=None, description="User identifier")
    session_id: UUID | None = Field(default=None, description="Session identifier")
    environment: str = Field(default="", description="Execution environment")
    resource_pool: str = Field(default="", description="Resource pool identifier")
    trace_enabled: bool = Field(default=False, description="Whether tracing is enabled")


class ModelWorkflowInputParameters(BaseModel):
    """Structured workflow input parameters."""

    execution_mode: str = Field(
        default="synchronous",
        description="Workflow execution mode",
    )
    retry_policy: str = Field(default="default", description="Retry policy name")
    timeout_seconds: int = Field(default=300, description="Workflow timeout in seconds")
    priority: str = Field(default="normal", description="Execution priority")
    debug_mode: bool = Field(default=False, description="Whether debug mode is enabled")
    validation_level: str = Field(
        default="strict",
        description="Input validation level",
    )
    custom_parameters: dict[str, str] = Field(
        default_factory=dict,
        description="Additional custom parameters",
    )


class ModelWorkflowConfiguration(BaseModel):
    """Structured workflow configuration settings."""

    checkpoint_enabled: bool = Field(
        default=True,
        description="Enable workflow checkpointing",
    )
    checkpoint_interval: int = Field(
        default=10,
        description="Checkpoint interval in steps",
    )
    error_handling_strategy: str = Field(
        default="stop_on_error",
        description="Error handling strategy",
    )
    monitoring_enabled: bool = Field(
        default=True,
        description="Enable workflow monitoring",
    )
    metrics_collection: bool = Field(
        default=True,
        description="Enable metrics collection",
    )
    notification_settings: dict[str, str] = Field(
        default_factory=dict,
        description="Notification configuration",
    )
    resource_limits: dict[str, str] = Field(
        default_factory=dict,
        description="Resource limit configuration",
    )


class ModelConditionalWorkflowContext(BaseModel):
    """Structured context for conditional workflow evaluation."""

    variable_scope: str = Field(
        default="local",
        description="Variable scope for condition",
    )
    evaluation_mode: str = Field(
        default="strict",
        description="Condition evaluation mode",
    )
    context_variables: dict[str, str] = Field(
        default_factory=dict,
        description="Context variables for evaluation",
    )
    external_dependencies: list[str] = Field(
        default_factory=list,
        description="External dependencies for condition",
    )
    cache_results: bool = Field(
        default=True,
        description="Whether to cache evaluation results",
    )


class ModelLoopWorkflowContext(BaseModel):
    """Structured context for loop workflow iterations."""

    iteration_counter: int = Field(default=0, description="Current iteration counter")
    loop_variable: str = Field(default="", description="Primary loop variable name")
    accumulator_variables: dict[str, str] = Field(
        default_factory=dict,
        description="Variables accumulated across iterations",
    )
    break_conditions: list[str] = Field(
        default_factory=list,
        description="Additional break conditions",
    )
    performance_tracking: bool = Field(
        default=True,
        description="Track performance metrics per iteration",
    )


# Discriminated workflow data types (defined after their dependencies)
class ModelWorkflowDataBase(BaseModel):
    """Base workflow data with discriminator."""

    workflow_type: EnumWorkflowType = Field(
        ...,
        description="Workflow type discriminator",
    )
    input_parameters: ModelWorkflowInputParameters = Field(
        default_factory=ModelWorkflowInputParameters,
        description="Structured workflow input parameters",
    )
    configuration: ModelWorkflowConfiguration = Field(
        default_factory=ModelWorkflowConfiguration,
        description="Structured workflow configuration settings",
    )


class ModelSequentialWorkflowData(ModelWorkflowDataBase):
    """Sequential workflow execution data."""

    workflow_type: Literal[EnumWorkflowType.SEQUENTIAL] = Field(
        default=EnumWorkflowType.SEQUENTIAL,
        description="Sequential workflow type",
    )
    step_sequence: list[str] = Field(
        ...,
        description="Ordered sequence of workflow steps",
    )
    continue_on_error: bool = Field(
        default=False,
        description="Whether to continue on step failure",
    )
    checkpoint_interval: int = Field(
        default=1,
        description="Number of steps between checkpoints",
    )
    rollback_strategy: str = Field(
        default="stop",
        description="Rollback strategy on failure",
    )


class ModelParallelWorkflowData(ModelWorkflowDataBase):
    """Parallel workflow execution data."""

    workflow_type: Literal[EnumWorkflowType.PARALLEL] = Field(
        default=EnumWorkflowType.PARALLEL,
        description="Parallel workflow type",
    )
    parallel_branches: list[list[str]] = Field(
        ...,
        description="Parallel execution branches",
    )
    synchronization_points: list[str] = Field(
        default_factory=list,
        description="Points where parallel branches synchronize",
    )
    max_concurrency: int = Field(
        default=4,
        description="Maximum number of parallel executions",
    )
    failure_strategy: str = Field(
        default="fail_fast",
        description="Strategy when parallel branch fails",
    )


class ModelConditionalWorkflowData(ModelWorkflowDataBase):
    """Conditional workflow execution data."""

    workflow_type: Literal[EnumWorkflowType.CONDITIONAL] = Field(
        default=EnumWorkflowType.CONDITIONAL,
        description="Conditional workflow type",
    )
    condition_expression: str = Field(..., description="Boolean condition expression")
    true_branch: list[str] = Field(
        ...,
        description="Steps to execute when condition is true",
    )
    false_branch: list[str] = Field(
        default_factory=list,
        description="Steps to execute when condition is false",
    )
    condition_context: ModelConditionalWorkflowContext = Field(
        default_factory=ModelConditionalWorkflowContext,
        description="Structured context variables for condition evaluation",
    )


class ModelLoopWorkflowData(ModelWorkflowDataBase):
    """Loop workflow execution data."""

    workflow_type: Literal[EnumWorkflowType.LOOP] = Field(
        default=EnumWorkflowType.LOOP,
        description="Loop workflow type",
    )
    loop_body: list[str] = Field(
        ...,
        description="Steps to execute in each loop iteration",
    )
    loop_condition: str = Field(..., description="Loop continuation condition")
    max_iterations: int = Field(
        default=100,
        description="Maximum number of loop iterations",
    )
    iteration_context: ModelLoopWorkflowContext = Field(
        default_factory=ModelLoopWorkflowContext,
        description="Structured context variables updated each iteration",
    )
    break_on_error: bool = Field(
        default=True,
        description="Whether to break loop on error",
    )


# Main workflow payload class (defined after all dependencies)
class ModelWorkflowPayload(BaseModel):
    """
    Strongly-typed workflow payload with discriminated unions.

    Replaces dict[str, Any] with discriminated workflow payload types.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    workflow_type: EnumWorkflowType = Field(
        ...,
        description="Discriminated workflow type",
    )
    workflow_data: (
        ModelSequentialWorkflowData
        | ModelParallelWorkflowData
        | ModelConditionalWorkflowData
        | ModelLoopWorkflowData
    ) = Field(
        ...,
        description="Workflow-specific data with discriminated union",
        discriminator="workflow_type",
    )
    execution_context: ModelWorkflowExecutionContext = Field(
        default_factory=ModelWorkflowExecutionContext,
        description="Structured workflow execution context",
    )
    state_data: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Workflow state data with proper typing",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Try common ID field patterns
        for field in [
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"{self.__class__.__name__}_{id(self)}"

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False


# Export for use
__all__ = ["ModelWorkflowPayload"]
