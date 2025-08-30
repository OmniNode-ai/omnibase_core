"""
Task Execution Context Model

ONEX-compliant execution context for idle compute tasks with proper typing
and structured metadata handling.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Dict, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from omnibase_core.model.runtime.model_idle_compute_task import \
        ModelResourceRequirements


class ModelTaskExecutionContext(BaseModel):
    """Execution context for idle compute tasks."""

    execution_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique execution identifier",
    )

    submitter_id: str = Field(
        default="unknown", description="ID of entity that submitted the task"
    )

    environment: str = Field(default="production", description="Execution environment")

    trace_id: Optional[str] = Field(default=None, description="Distributed trace ID")

    debug_enabled: bool = Field(
        default=False, description="Whether debug mode is enabled"
    )

    resource_constraints: Optional["ModelResourceRequirements"] = Field(
        default=None, description="Specific resource constraints for this execution"
    )

    execution_metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="String-only metadata for execution (logging, tagging, etc.)",
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
