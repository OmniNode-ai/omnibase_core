"""
Effect Operation Result Model.

Strongly-typed result for a single effect operation.
Eliminates dict[str, Any] in favor of explicit fields.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue

__all__ = ["ModelEffectOperationResult"]


class ModelEffectOperationResult(BaseModel):
    """
    Strongly-typed result for a single effect operation.

    Eliminates dict[str, Any] in favor of explicit fields.
    Uses ModelSchemaValue for extracted_fields to comply with ONEX strong typing
    standards (no primitive soup unions).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    operation_name: str
    success: bool
    retries: int = Field(default=0, ge=0)
    duration_ms: float = Field(ge=0)
    extracted_fields: dict[str, ModelSchemaValue] = Field(default_factory=dict)
    error_message: str | None = None
    error_code: str | None = None
