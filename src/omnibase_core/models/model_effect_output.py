"""
ModelEffectOutput - Output model for NodeEffect operations.

Strongly typed output wrapper with transaction status and side effect execution metadata.

Author: ONEX Framework Team
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_effect_types import EnumEffectType, EnumTransactionState

__all__ = ["ModelEffectOutput"]


class ModelEffectOutput(BaseModel):
    """
    Output model for NodeEffect operations.

    Strongly typed output wrapper with transaction status
    and side effect execution metadata.
    """

    result: str | int | float | bool | dict[str, Any] | list[Any]
    operation_id: UUID
    effect_type: EnumEffectType
    transaction_state: EnumTransactionState
    processing_time_ms: float
    retry_count: int = 0
    side_effects_applied: list[str] = Field(default_factory=list)
    rollback_operations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
