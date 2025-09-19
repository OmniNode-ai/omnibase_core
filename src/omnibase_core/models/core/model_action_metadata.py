"""
Action Metadata Model.

Provides detailed metadata tracking for node actions with UUID correlation and trust scoring.
Enhanced for tool-as-a-service architecture with strong typing throughout.
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_performance_metrics import ModelPerformanceMetrics
from omnibase_core.models.core.model_security_context import ModelSecurityContext
from omnibase_core.models.core.model_trust_level import ModelTrustLevel
from omnibase_core.models.nodes.model_node_action_type import ModelNodeActionType


class ModelActionMetadata(BaseModel):
    """
    Enhanced metadata for node actions with UUID tracking and trust scores.

    Provides comprehensive tracking for action execution with strong typing
    and support for tool-as-a-service architecture.
    """

    # Core identification
    action_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this action instance",
    )
    action_type: ModelNodeActionType = Field(..., description="Rich action type model")
    action_name: str = Field(..., description="Human-readable action name")

    # Correlation tracking
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Correlation ID for tracking across system boundaries",
    )
    parent_correlation_id: UUID | None = Field(
        None,
        description="Parent correlation ID for action chaining",
    )
    session_id: UUID | None = Field(
        None,
        description="Session ID for grouping related actions",
    )

    # Trust and security
    trust_score: ModelTrustLevel = Field(
        default_factory=ModelTrustLevel.trusted,
        description="Rich trust level for action execution with verification support",
    )
    security_context: ModelSecurityContext = Field(
        default_factory=lambda: ModelSecurityContext(
            user_id=None,
            role=None,
            authentication_method=None,
            ip_address=None,
            user_agent=None,
            session_token=None,
        ),
        description="Structured security context and permissions",
    )

    # Timing and execution
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the action was created",
    )
    started_at: datetime | None = Field(
        None,
        description="When action execution started",
    )
    completed_at: datetime | None = Field(
        None,
        description="When action execution completed",
    )
    timeout_seconds: int | None = Field(
        None,
        description="Action timeout in seconds",
    )

    # Execution context
    execution_context: dict[str, str | int | float | bool] = Field(
        default_factory=lambda: {},
        description="Execution environment and context",
    )
    parameters: dict[str, str | int | float | bool | list[str]] = Field(
        default_factory=lambda: {},
        description="Action parameters with strong typing",
    )

    # Results and status
    status: str = Field(default="created", description="Current action status")
    result_data: dict[str, str | int | float | bool | list[str]] | None = Field(
        None,
        description="Action result data",
    )
    error_details: dict[str, str | int | bool] | None = Field(
        None,
        description="Error details if action failed",
    )

    # Tool-as-a-service metadata
    service_metadata: dict[str, str | int | float | bool | list[str]] = Field(
        default_factory=lambda: {},
        description="Service discovery and composition metadata",
    )
    tool_discovery_tags: list[str] = Field(
        default_factory=list,
        description="Tags for tool discovery and categorization",
    )
    mcp_endpoint: str | None = Field(
        None,
        description="MCP endpoint for this action",
    )
    graphql_endpoint: str | None = Field(
        None,
        description="GraphQL endpoint for this action",
    )

    # Performance tracking
    performance_metrics: ModelPerformanceMetrics = Field(
        default_factory=lambda: ModelPerformanceMetrics(
            execution_time_ms=None,
            memory_usage_mb=None,
            cpu_usage_percent=None,
            io_operations=None,
            network_requests=None,
            cache_hits=None,
            cache_misses=None,
        ),
        description="Structured performance metrics for this action",
    )
    resource_usage: dict[str, int | float] = Field(
        default_factory=lambda: {},
        description="Resource usage metrics",
    )

    def mark_started(self) -> None:
        """Mark the action as started."""
        self.started_at = datetime.utcnow()
        self.status = "running"

    def mark_completed(
        self,
        result_data: dict[str, str | int | float | bool | list[str]] | None = None,
    ) -> None:
        """Mark the action as completed with optional result data."""
        self.completed_at = datetime.utcnow()
        self.status = "completed"
        if result_data:
            self.result_data = result_data

    def mark_failed(self, error_details: dict[str, str | int | bool]) -> None:
        """Mark the action as failed with error details."""
        self.completed_at = datetime.utcnow()
        self.status = "failed"
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
                f"Use one of: {list(self.performance_metrics.__fields__.keys())}"
            )
            raise ValueError(
                msg,
            )
        setattr(self.performance_metrics, name, value)

    def add_resource_usage(self, resource: str, usage: int | float) -> None:
        """Add resource usage information."""
        self.resource_usage[resource] = usage

    def to_service_discovery_metadata(
        self,
    ) -> dict[
        str,
        str
        | bool
        | list[str]
        | int
        | None
        | float
        | None
        | dict[str, str | int | float | bool | list[str]],
    ]:
        """Generate metadata for service discovery with strong typing."""
        return {
            "action_id": str(self.action_id),
            "action_type": self.action_type.name,
            "action_name": self.action_name,
            "correlation_id": str(self.correlation_id),
            "trust_score": self.trust_score.trust_score,
            "status": self.status,
            "mcp_endpoint": self.mcp_endpoint,
            "graphql_endpoint": self.graphql_endpoint,
            "tool_discovery_tags": self.tool_discovery_tags,
            "service_metadata": self.service_metadata,
            "execution_duration": self.get_execution_duration(),
        }

    def validate_trust_score(self) -> bool:
        """Validate that the trust score is within acceptable bounds."""
        return bool(self.trust_score.is_trusted())

    def is_expired(self) -> bool:
        """Check if the action has expired based on timeout."""
        if not self.timeout_seconds or not self.created_at:
            return False

        elapsed = (datetime.utcnow() - self.created_at).total_seconds()
        return elapsed > self.timeout_seconds

    def can_execute(self, minimum_trust_score: float = 0.0) -> bool:
        """Check if the action can be executed based on trust score and expiration."""
        return (
            self.trust_score.is_trusted(minimum_trust_score)
            and not self.is_expired()
            and self.status in ["created", "ready"]
        )
