import uuid
from typing import Any

from pydantic import Field

"""Effect input model for side effect operations."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_effect_type import EnumEffectType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelEffectInput(BaseModel):
    """
    Input model for NodeEffect operations.

    Strongly typed input wrapper for side effect operations
    with transaction and retry configuration.
    """

    effect_type: EnumEffectType
    operation_data: dict[str, ModelSchemaValue]
    operation_id: UUID | None = Field(default_factory=uuid4)
    transaction_enabled: bool = True
    retry_enabled: bool = True
    max_retries: int = 3
    retry_delay_ms: int = 1000
    circuit_breaker_enabled: bool = False
    timeout_ms: int = 30000
    metadata: dict[str, ModelSchemaValue] | None = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
