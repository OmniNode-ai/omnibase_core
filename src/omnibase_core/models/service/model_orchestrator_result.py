from pydantic import Field

"""
Orchestrator result model.
"""

from pydantic import BaseModel, Field

from .model_orchestrator_graph import ModelOrchestratorGraph
from .model_orchestrator_output import ModelOrchestratorOutput
from .model_orchestrator_plan import ModelOrchestratorPlan


class ModelOrchestratorResult(BaseModel):
    """Orchestrator result model."""

    # Result identification
    result_id: str = Field(..., description="Result identifier")
    status: str = Field(..., description="Orchestration status")

    # Execution details
    graph: ModelOrchestratorGraph | None = Field(default=None, description="Graph used")
    plan: ModelOrchestratorPlan | None = Field(
        default=None, description="Plan executed"
    )

    # Structured output
    output: ModelOrchestratorOutput | None = Field(
        default=None,
        description="Orchestration output",
    )
