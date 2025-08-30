"""
Orchestrator plan model.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from ..core.model_custom_fields import ModelCustomFields
from .model_orchestrator_step import ModelOrchestratorStep


class ModelOrchestratorPlan(BaseModel):
    """ONEX plan model for orchestrator."""

    # Plan identification
    plan_id: str = Field(..., description="Plan identifier")
    plan_name: str = Field(..., description="Plan name")

    # Plan structure
    steps: List[ModelOrchestratorStep] = Field(
        default_factory=list, description="Plan steps"
    )

    # Plan metadata using structured fields
    description: Optional[str] = Field(None, description="Plan description")
    version: Optional[str] = Field(None, description="Plan version")
    created_at: Optional[str] = Field(None, description="Plan creation timestamp")
    author: Optional[str] = Field(None, description="Plan author")

    # Custom metadata for extensibility
    custom_metadata: Optional[ModelCustomFields] = Field(
        None, description="Custom metadata fields"
    )
