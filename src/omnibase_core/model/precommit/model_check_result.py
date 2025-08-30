"""Model for pre-commit check results."""

from typing import List

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_onex_status import EnumOnexStatus

from .model_violation import ModelViolation


class ModelCheckResult(BaseModel):
    """Result of a pre-commit check operation."""

    status: EnumOnexStatus = Field(..., description="Overall check status")
    violations: List[ModelViolation] = Field(
        default_factory=list, description="List of violations found"
    )
    files_checked: int = Field(0, description="Number of files checked")
    critical_count: int = Field(0, description="Number of critical violations")
    high_count: int = Field(0, description="Number of high severity violations")
    medium_count: int = Field(0, description="Number of medium severity violations")
    low_count: int = Field(0, description="Number of low severity violations")
    info_count: int = Field(0, description="Number of info level violations")
    message: str = Field("", description="Summary message")
