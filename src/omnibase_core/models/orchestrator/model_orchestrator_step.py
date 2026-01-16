from pydantic import Field

"\nOrchestrator Step Model\n\nType-safe orchestrator step that replaces Dict[str, Any] usage\nin orchestrator plans.\n"
from uuid import UUID

from pydantic import BaseModel

from omnibase_core.models.services.model_custom_fields import ModelCustomFields


class ModelOrchestratorStep(BaseModel):
    """
    Type-safe orchestrator step.

    Represents a single step in an orchestrator plan with
    structured fields for common step attributes.
    """

    step_id: UUID = Field(default=..., description="Unique step identifier")
    name: str = Field(default=..., description="Step name")
    step_type: str = Field(
        default=..., description="Type of step (e.g., 'node', 'condition', 'parallel')"
    )
    node_name: str | None = Field(
        default=None, description="Node to execute (for node steps)"
    )
    action: str | None = Field(default=None, description="Action to perform")
    inputs: ModelCustomFields | None = Field(
        default=None, description="Step input parameters"
    )
    timeout_seconds: int | None = Field(
        default=None, description="Step timeout in seconds"
    )
    retry_count: int | None = Field(
        default=None, description="Number of retries allowed"
    )
    depends_on: list[str] = Field(
        default_factory=list, description="List of step IDs this depends on"
    )
    condition: str | None = Field(
        default=None, description="Condition expression for conditional steps"
    )
    parallel_steps: list[str] | None = Field(
        default=None, description="Steps to run in parallel"
    )
    output_mapping: dict[str, str] | None = Field(
        default=None, description="Map step outputs to plan variables"
    )
    continue_on_error: bool = Field(
        default=False, description="Whether to continue if step fails"
    )
    description: str | None = Field(default=None, description="Step description")
    custom_fields: ModelCustomFields | None = Field(
        default=None, description="Custom fields for step-specific data"
    )


__all__ = ["ModelOrchestratorStep"]
