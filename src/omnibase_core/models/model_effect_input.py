"""
VERSION: 1.0.0
STABILITY GUARANTEE: Model structure frozen.
Breaking changes require major version bump.

ModelEffectInput - Input model for NodeEffect operations.

Strongly typed input wrapper for side effect operations with transaction
and retry configuration.

Author: ONEX Framework Team
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_effect_types import EnumEffectType


class ModelEffectInput(BaseModel):
    """
    Input model for NodeEffect operations.

    Strongly typed input wrapper for side effect operations
    with transaction and retry configuration.
    """

    effect_type: EnumEffectType
    operation_data: dict[str, Any]
    operation_id: UUID = Field(default_factory=uuid4)
    transaction_enabled: bool = True
    retry_enabled: bool = True
    max_retries: int = 3
    retry_delay_ms: int = 1000
    circuit_breaker_enabled: bool = False
    timeout_ms: int = 30000
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


__all__ = ["ModelEffectInput"]
