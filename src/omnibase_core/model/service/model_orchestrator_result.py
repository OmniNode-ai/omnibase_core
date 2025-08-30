"""
Orchestrator result model.
"""

from typing import Optional

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
    graph: Optional[ModelOrchestratorGraph] = Field(None, description="Graph used")
    plan: Optional[ModelOrchestratorPlan] = Field(None, description="Plan executed")

    # Structured output
    output: Optional[ModelOrchestratorOutput] = Field(
        None, description="Orchestration output"
    )
