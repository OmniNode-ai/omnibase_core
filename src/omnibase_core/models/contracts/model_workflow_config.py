from pydantic import Field

from omnibase_core.models.core.model_workflow import ModelWorkflow

"""
Workflow Configuration Model - ONEX Standards Compliant.

Defines workflow execution patterns, state persistence,
and coordination strategies for complex workflows.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any

from pydantic import BaseModel


class ModelWorkflowConfig(BaseModel):
    """
    Workflow coordination and state management.

    Defines workflow execution patterns, state persistence,
    and coordination strategies for complex workflows.
    """

    execution_mode: str = Field(
        default="sequential",
        description="Workflow execution mode (sequential, parallel, mixed)",
    )

    max_parallel_branches: int = Field(
        default=4,
        description="Maximum parallel execution branches",
        ge=1,
    )

    checkpoint_enabled: bool = Field(
        default=True,
        description="Enable workflow checkpointing",
    )

    checkpoint_interval_ms: int = Field(
        default=5000,
        description="Checkpoint interval in milliseconds",
        ge=100,
    )

    state_persistence_enabled: bool = Field(
        default=True,
        description="Enable workflow state persistence",
    )

    rollback_enabled: bool = Field(
        default=True,
        description="Enable workflow rollback capabilities",
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Workflow execution timeout in milliseconds",
        ge=1,
    )

    recovery_enabled: bool = Field(
        default=True,
        description="Enable automatic workflow recovery",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
