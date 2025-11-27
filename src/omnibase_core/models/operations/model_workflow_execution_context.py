from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ModelWorkflowExecutionContext(BaseModel):
    """Structured workflow execution context."""

    execution_id: UUID = Field(
        default_factory=uuid4,
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
