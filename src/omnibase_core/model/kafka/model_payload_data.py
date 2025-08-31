"""ModelPayloadData: Strongly typed envelope payload data"""

from pydantic import BaseModel, Field

from omnibase_core.model.kafka.model_intelligence_result import ModelIntelligenceResult
from omnibase_core.model.kafka.model_rule_context import ModelRuleContext


class ModelPayloadData(BaseModel):
    """Strongly typed envelope payload data"""

    payload_type: str = Field(..., description="Type of payload")
    data: ModelIntelligenceResult | ModelRuleContext | dict[str, str] = Field(
        ...,
        description="Typed payload data",
    )
