import uuid
from typing import Any

from pydantic import Field

from .model_config import ModelConfig

"""Effect output model for side effect operation results."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_effect_type import EnumEffectType
from omnibase_core.enums.enum_transaction_state import EnumTransactionState
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.operations.model_effect_result import ModelEffectResult


class ModelEffectOutput(BaseModel):
    """
    Output model for NodeEffect operations.

    Strongly typed output wrapper with transaction status
    and side effect execution metadata using discriminated union for results.
    """

    result: ModelEffectResult
    operation_id: UUID
    effect_type: EnumEffectType
    transaction_state: EnumTransactionState
    processing_time_ms: float
    retry_count: int = 0
    side_effects_applied: list[str] | None = Field(default_factory=list)
    rollback_operations: list[str] | None = Field(default_factory=list)
    metadata: dict[str, ModelSchemaValue] | None = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
