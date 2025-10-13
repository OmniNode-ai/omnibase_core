"""ModelPolicyEvaluationDetails: Details from policy evaluation."""

from pydantic import BaseModel, Field

from .model_evaluation_context import ModelEvaluationContext
from .model_evaluation_models import (
    ModelAuthorizationEvaluation,
    ModelComplianceEvaluation,
    ModelSignatureEvaluation,
)


class ModelPolicyEvaluationDetails(BaseModel):
    """Detailed information from policy evaluation."""

    policy_name: str | None = Field(default=None, description="Policy name")
    context: ModelEvaluationContext | None = Field(
        default=None,
        description="Evaluation context",
    )
    signature_evaluation: ModelSignatureEvaluation | None = Field(
        default=None,
        description="Signature evaluation result",
    )
    compliance_evaluation: ModelComplianceEvaluation | None = Field(
        default=None,
        description="Compliance evaluation result",
    )
    authorization_evaluation: ModelAuthorizationEvaluation | None = Field(
        default=None,
        description="Authorization evaluation result",
    )
    enforcement_mode: str | None = Field(default=None, description="Enforcement mode")
    cache_timestamp: str | None = Field(default=None, description="Cache timestamp")
    error: str | None = Field(
        default=None, description="Error message if evaluation failed"
    )
