"""ModelPolicyEvaluationDetails: Details from policy evaluation."""

from typing import Optional

from pydantic import BaseModel, Field

from .model_evaluation_context import ModelEvaluationContext
from .model_evaluation_models import (ModelAuthorizationEvaluation,
                                      ModelComplianceEvaluation,
                                      ModelSignatureEvaluation)


class ModelPolicyEvaluationDetails(BaseModel):
    """Detailed information from policy evaluation."""

    policy_name: Optional[str] = Field(None, description="Policy name")
    context: Optional[ModelEvaluationContext] = Field(
        None, description="Evaluation context"
    )
    signature_evaluation: Optional[ModelSignatureEvaluation] = Field(
        None, description="Signature evaluation result"
    )
    compliance_evaluation: Optional[ModelComplianceEvaluation] = Field(
        None, description="Compliance evaluation result"
    )
    authorization_evaluation: Optional[ModelAuthorizationEvaluation] = Field(
        None, description="Authorization evaluation result"
    )
    enforcement_mode: Optional[str] = Field(None, description="Enforcement mode")
    cache_timestamp: Optional[str] = Field(None, description="Cache timestamp")
    error: Optional[str] = Field(None, description="Error message if evaluation failed")

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True
