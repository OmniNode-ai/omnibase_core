"""ModelPolicyEvaluationDetails: Details from policy evaluation."""

from pydantic import BaseModel, Field

from .model_config import ModelConfig
from .model_evaluation_context import ModelEvaluationContext
from .model_evaluation_models import (
    ModelAuthorizationEvaluation,
    ModelComplianceEvaluation,
    ModelSignatureEvaluation,
)


class ModelPolicyEvaluationDetails(BaseModel):
    """Detailed information from policy evaluation."""

    policy_name: str | None = Field(None, description="Policy name")
    context: ModelEvaluationContext | None = Field(
        None,
        description="Evaluation context",
    )
    signature_evaluation: ModelSignatureEvaluation | None = Field(
        None,
        description="Signature evaluation result",
    )
    compliance_evaluation: ModelComplianceEvaluation | None = Field(
        None,
        description="Compliance evaluation result",
    )
    authorization_evaluation: ModelAuthorizationEvaluation | None = Field(
        None,
        description="Authorization evaluation result",
    )
    enforcement_mode: str | None = Field(None, description="Enforcement mode")
    cache_timestamp: str | None = Field(None, description="Cache timestamp")
    error: str | None = Field(None, description="Error message if evaluation failed")
