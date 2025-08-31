"""
Orchestrator Step Model

Type-safe orchestrator step that replaces Dict[str, Any] usage
in orchestrator plans.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_custom_fields import ModelCustomFields


class ModelOrchestratorStep(BaseModel):
    """
    Type-safe orchestrator step.

    Represents a single step in an orchestrator plan with
    structured fields for common step attributes.
    """

    # Step identification
    step_id: str = Field(..., description="Unique step identifier")
    name: str = Field(..., description="Step name")
    step_type: str = Field(
        ...,
        description="Type of step (e.g., 'node', 'condition', 'parallel')",
    )

    # Execution details
    node_name: str | None = Field(
        None,
        description="Node to execute (for node steps)",
    )
    action: str | None = Field(None, description="Action to perform")

    # Step configuration
    inputs: dict[str, Any] | None = Field(None, description="Step input parameters")
    timeout_seconds: int | None = Field(None, description="Step timeout in seconds")
    retry_count: int | None = Field(None, description="Number of retries allowed")

    # Dependencies and flow control
    depends_on: list[str] = Field(
        default_factory=list,
        description="List of step IDs this depends on",
    )
    condition: str | None = Field(
        None,
        description="Condition expression for conditional steps",
    )
    parallel_steps: list[str] | None = Field(
        None,
        description="Steps to run in parallel",
    )

    # Output handling
    output_mapping: dict[str, str] | None = Field(
        None,
        description="Map step outputs to plan variables",
    )
    continue_on_error: bool = Field(
        False,
        description="Whether to continue if step fails",
    )

    # Metadata
    description: str | None = Field(None, description="Step description")
    custom_fields: ModelCustomFields | None = Field(
        None,
        description="Custom fields for step-specific data",
    )
