"""Evaluation models to break circular imports between model_metadata.py and model_policy_evaluation_details.py"""

from typing import Dict, List

from pydantic import BaseModel, Field


class ModelSignatureEvaluation(BaseModel):
    """Signature evaluation result model."""

    is_valid: bool = Field(
        default=False, description="Whether signature evaluation passed"
    )
    violations: List[str] = Field(
        default_factory=list, description="Signature violations found"
    )
    warnings: List[str] = Field(default_factory=list, description="Signature warnings")
    meets_requirements: bool = Field(
        default=False, description="Whether signature meets requirements"
    )


class ModelComplianceEvaluation(BaseModel):
    """Compliance evaluation result model."""

    status: Dict[str, bool] = Field(
        default_factory=dict, description="Compliance framework status"
    )
    violations: List[str] = Field(
        default_factory=list, description="Compliance violations found"
    )
    warnings: List[str] = Field(default_factory=list, description="Compliance warnings")
    meets_requirements: bool = Field(
        default=False, description="Whether compliance requirements are met"
    )


class ModelAuthorizationEvaluation(BaseModel):
    """Authorization evaluation result model."""

    violations: List[str] = Field(
        default_factory=list, description="Authorization violations found"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Authorization warnings"
    )
    meets_requirements: bool = Field(
        default=False, description="Whether authorization requirements are met"
    )
