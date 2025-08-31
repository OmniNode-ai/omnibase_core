"""ModelRuleContext: Strongly typed rule decision context"""

from pydantic import BaseModel, Field


class ModelRuleContext(BaseModel):
    """Strongly typed rule decision context"""

    rule_id: str = Field(..., description="Rule identifier")
    entity_type: str = Field(..., description="Type of entity being evaluated")
    entity_id: str = Field(..., description="Identifier of entity")
    conditions_met: dict[str, str] = Field(
        default_factory=dict,
        description="Met conditions",
    )
    decision_factors: dict[str, str] = Field(
        default_factory=dict,
        description="Decision factors",
    )
    timestamp: str = Field(..., description="ISO timestamp of evaluation")
