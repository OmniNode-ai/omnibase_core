"""
Action Metadata Model.

Provides detailed metadata tracking for node actions with UUID correlation and trust scoring.
Enhanced for tool-as-a-service architecture with strong typing throughout.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_general_status import EnumGeneralStatus
from omnibase_core.models.core.model_core_performance_metrics import (
    ModelPerformanceMetrics,
)
from omnibase_core.models.core.model_execution_context import ModelExecutionContext
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.security.model_security_context import ModelSecurityContext
from omnibase_core.models.services.model_error_details import ModelErrorDetails
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelActionMetadata(BaseModel):
    """
    Enhanced metadata for node actions with UUID tracking and trust scores.

    Provides comprehensive tracking for action execution with strong typing
    and support for tool-as-a-service architecture.

    Optional Fields Rationale:
        - action_type: Optional to allow default construction; should be set during
          action initialization for type safety and introspection.
        - parent_correlation_id/session_id: Optional for standalone actions without
          parent context or session grouping.
        - started_at/completed_at: Populated via mark_started()/mark_completed()
          lifecycle methods, not at construction time.
        - timeout_seconds: Optional for actions without timeout constraints.
        - execution_context: Optional for actions not requiring environment context
          (development vs. production, resource limits, etc.).
        - result_data/error_details: Populated only after action completion or failure.
        - mcp_endpoint/graphql_endpoint: Optional for nodes not exposing these
          protocol endpoints.
    """

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
    )

    # Core identification
    action_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this action instance",
    )
    action_type: ModelNodeActionType | None = Field(
        default=None,
        description="Rich action type model (optional for default construction)",
    )
    action_name: str = Field(
        default="",
        description="Human-readable action name (empty for default construction)",
    )

    # Correlation tracking
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Correlation ID for tracking across system boundaries",
    )
    parent_correlation_id: UUID | None = Field(
        default=None,
        description="Parent correlation ID for action chaining",
    )
    session_id: UUID | None = Field(
        default=None,
        description="Session ID for grouping related actions",
    )

    # Trust and security
    trust_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Trust score for action execution (0.0-1.0)",
    )
    security_context: ModelSecurityContext = Field(
        default_factory=ModelSecurityContext,
        description="Structured security context and permissions",
    )

    # Timing and execution
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the action was created",
    )
    started_at: datetime | None = Field(
        default=None,
        description="When action execution started",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When action execution completed",
    )
    timeout_seconds: int | None = Field(
        default=None,
        description="Action timeout in seconds",
    )

    # Execution context
    execution_context: ModelExecutionContext | None = Field(
        default=None,
        description="Execution environment and context",
    )
    parameters: SerializedDict = Field(
        default_factory=dict,
        description="Action parameters as JSON-serializable data",
    )

    # Results and status
    status: EnumGeneralStatus = Field(
        default=EnumGeneralStatus.CREATED, description="Current action status"
    )
    result_data: SerializedDict | None = Field(
        default=None,
        description="Action result data as JSON-serializable data",
    )
    error_details: ModelErrorDetails[Any] | None = Field(
        default=None,
        description="Structured error details if action failed",
    )

    # Tool-as-a-service metadata
    service_metadata: SerializedDict = Field(
        default_factory=dict,
        description="Service discovery and composition metadata as JSON-serializable data",
    )
    tool_discovery_tags: list[str] = Field(
        default_factory=list,
        description="Tags for tool discovery and categorization",
    )
    mcp_endpoint: str | None = Field(
        default=None,
        description="MCP endpoint for this action",
    )
    graphql_endpoint: str | None = Field(
        default=None,
        description="GraphQL endpoint for this action",
    )

    # Performance tracking
    performance_metrics: ModelPerformanceMetrics = Field(
        default_factory=ModelPerformanceMetrics,
        description="Structured performance metrics for this action",
    )
    resource_usage: dict[str, int | float] = Field(
        default_factory=dict,
        description="Resource usage metrics",
    )

    def mark_started(self) -> None:
        """Mark the action as started."""
        self.started_at = datetime.now(UTC)
        self.status = EnumGeneralStatus.RUNNING

    def mark_completed(
        self,
        result_data: SerializedDict | None = None,
    ) -> None:
        """Mark the action as completed with optional result data."""
        self.completed_at = datetime.now(UTC)
        self.status = EnumGeneralStatus.COMPLETED
        if result_data:
            self.result_data = result_data

    def mark_failed(self, error_details: ModelErrorDetails[Any]) -> None:
        """Mark the action as failed with structured error details."""
        self.completed_at = datetime.now(UTC)
        self.status = EnumGeneralStatus.FAILED
        self.error_details = error_details

    def get_execution_duration(self) -> float | None:
        """Get the execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def add_performance_metric(self, name: str, value: int | float) -> None:
        """Add a performance metric."""
        if not hasattr(self.performance_metrics, name):
            msg = (
                f"Performance metric '{name}' is not supported. "
                f"Use one of: {list(self.performance_metrics.model_fields.keys())}"
            )
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        setattr(self.performance_metrics, name, value)

    def add_resource_usage(self, resource: str, usage: int | float) -> None:
        """Add resource usage information."""
        self.resource_usage[resource] = usage

    def to_service_discovery_metadata(
        self,
    ) -> dict[str, object]:
        """Generate metadata for service discovery as JSON-serializable data."""
        return {
            "action_id": str(self.action_id),
            "action_type": self.action_type.name if self.action_type else None,
            "action_name": self.action_name,
            "correlation_id": str(self.correlation_id),
            "trust_score": self.trust_score,
            "status": self.status,
            "mcp_endpoint": self.mcp_endpoint,
            "graphql_endpoint": self.graphql_endpoint,
            "tool_discovery_tags": self.tool_discovery_tags,
            "service_metadata": self.service_metadata,
            "execution_duration": self.get_execution_duration(),
        }

    def validate_trust_score(self) -> bool:
        """Validate that the trust score is within acceptable bounds."""
        return 0.0 <= self.trust_score <= 1.0

    def is_expired(self) -> bool:
        """Check if the action has expired based on timeout."""
        if not self.timeout_seconds or not self.created_at:
            return False

        elapsed = (datetime.now(UTC) - self.created_at).total_seconds()
        return elapsed > self.timeout_seconds

    def can_execute(self, minimum_trust_score: float = 0.0) -> bool:
        """Check if the action can be executed based on trust score and expiration."""
        return (
            self.trust_score >= minimum_trust_score
            and not self.is_expired()
            and self.status in {EnumGeneralStatus.CREATED, EnumGeneralStatus.PENDING}
        )
