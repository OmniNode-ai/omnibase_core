from typing import Dict, Optional

from pydantic import Field
from uuid import UUID

"""
Orchestrator info model to replace Dict[str, Any] usage for orchestrator_info fields.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from omnibase_core.models.core.model_orchestrator_metrics import (
    ModelOrchestratorMetrics,
)


class ModelOrchestratorInfo(BaseModel):
    """
    Orchestrator information with typed fields.
    Replaces Dict[str, Any] for orchestrator_info fields.
    """

    # Orchestrator identification
    orchestrator_id: str = Field(
        default=..., description="Unique orchestrator identifier"
    )
    orchestrator_type: str = Field(
        default=...,
        description="Orchestrator type (kubernetes/swarm/nomad/custom)",
    )
    orchestrator_version: str = Field(default=..., description="Orchestrator version")

    # Cluster information
    cluster_name: str | None = Field(default=None, description="Cluster name")
    cluster_region: str | None = Field(default=None, description="Cluster region")
    cluster_zone: str | None = Field(
        default=None, description="Cluster availability zone"
    )

    # Node information
    node_id: UUID | None = Field(default=None, description="Node identifier")
    node_name: str | None = Field(default=None, description="Node name")
    node_role: str | None = Field(
        default=None, description="Node role (master/worker/edge)"
    )

    # Workflow information
    workflow_id: UUID | None = Field(default=None, description="Current workflow ID")
    workflow_name: str | None = Field(default=None, description="Workflow name")
    workflow_step: str | None = Field(default=None, description="Current workflow step")
    workflow_status: str | None = Field(default=None, description="Workflow status")

    # Execution context
    execution_id: UUID | None = Field(default=None, description="Execution identifier")
    parent_execution_id: str | None = Field(
        default=None, description="Parent execution ID"
    )
    root_execution_id: str | None = Field(default=None, description="Root execution ID")

    # Timing information
    scheduled_at: datetime | None = Field(
        default=None,
        description="Scheduled execution time",
    )
    started_at: datetime | None = Field(default=None, description="Actual start time")
    completed_at: datetime | None = Field(default=None, description="Completion time")

    # Resource allocation
    cpu_request: str | None = Field(
        default=None, description="CPU request (e.g., '100m')"
    )
    cpu_limit: str | None = Field(default=None, description="CPU limit (e.g., '1000m')")
    memory_request: str | None = Field(
        default=None,
        description="Memory request (e.g., '128Mi')",
    )
    memory_limit: str | None = Field(
        default=None,
        description="Memory limit (e.g., '512Mi')",
    )

    # Labels and annotations
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Orchestrator labels",
    )
    annotations: dict[str, str] = Field(
        default_factory=dict,
        description="Orchestrator annotations",
    )

    # Metrics
    metrics: ModelOrchestratorMetrics | None = Field(
        default=None,
        description="Orchestrator metrics",
    )

    # Service mesh information
    service_mesh: str | None = Field(
        default=None,
        description="Service mesh type (istio/linkerd/consul)",
    )
    sidecar_injected: bool = Field(
        default=False, description="Whether sidecar is injected"
    )

    # Custom orchestrator data
    custom_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom orchestrator-specific data",
    )

    model_config = ConfigDict()

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> Optional["ModelOrchestratorInfo"]:
        """Create from dict[str, Any]ionary for easy migration."""
        if data is None:
            return None

        # Handle legacy format
        if "orchestrator_id" not in data:
            data["orchestrator_id"] = data.get("id", "unknown")
        if "orchestrator_type" not in data:
            data["orchestrator_type"] = data.get("type", "custom")
        if "orchestrator_version" not in data:
            data["orchestrator_version"] = data.get("version", "unknown")

        return cls(**data)

    def get_resource_summary(self) -> str:
        """Get resource allocation summary."""
        parts = []
        if self.cpu_request:
            parts.append(f"CPU: {self.cpu_request}")
        if self.memory_request:
            parts.append(f"Memory: {self.memory_request}")
        return ", ".join(parts) if parts else "No resources specified"

    def is_completed(self) -> bool:
        """Check if orchestration is completed."""
        return self.workflow_status in ["completed", "succeeded", "failed", "cancelled"]

    @field_serializer("scheduled_at", "started_at", "completed_at")
    def serialize_datetime(self, value) -> None:
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
