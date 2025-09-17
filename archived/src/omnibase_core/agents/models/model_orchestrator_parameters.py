"""
Orchestrator Parameters Model

Workflow orchestrator parameters model for workflow execution configuration.
This provides a simpler interface specifically for the WorkflowOrchestratorAgent.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ModelOrchestratorParameters(BaseModel):
    """
    Workflow orchestrator parameters for execution configuration.

    This model provides the parameters specifically needed for workflow
    orchestration operations by the WorkflowOrchestratorAgent.
    """

    scenario_id: str = Field(..., description="Unique scenario identifier")
    correlation_id: str = Field(..., description="Correlation ID for tracking")
    execution_mode: str = Field(default="sequential", description="Execution mode")
    timeout_seconds: int = Field(
        default=300, description="Operation timeout in seconds"
    )
    retry_count: int = Field(default=3, description="Number of retry attempts")
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Additional metadata"
    )

    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """Get a metadata value with optional default."""
        if self.metadata is None:
            return default
        return self.metadata.get(key, default)

    def set_metadata_value(self, key: str, value: Any) -> None:
        """Set a metadata value."""
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value

    def has_metadata(self, key: str) -> bool:
        """Check if metadata key exists."""
        return self.metadata is not None and key in self.metadata
