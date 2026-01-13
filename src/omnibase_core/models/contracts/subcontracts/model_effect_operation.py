"""
Effect Operation Model.

Single effect operation definition with discriminated union IO config.
The `io_config` field uses a discriminated union based on `handler_type`.
This ensures type-safe validation at contract load time.
"""

from collections.abc import Mapping
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants.constants_effect_idempotency import IDEMPOTENCY_DEFAULTS
from omnibase_core.constants.constants_effect_limits import (
    EFFECT_OPERATION_DESCRIPTION_MAX_LENGTH,
    EFFECT_OPERATION_NAME_MAX_LENGTH,
    EFFECT_TIMEOUT_MAX_MS,
    EFFECT_TIMEOUT_MIN_MS,
)

from .model_effect_circuit_breaker import ModelEffectCircuitBreaker
from .model_effect_io_configs import (
    ModelDbIOConfig,
    ModelFilesystemIOConfig,
    ModelHttpIOConfig,
    ModelKafkaIOConfig,
)
from .model_effect_response_handling import ModelEffectResponseHandling
from .model_effect_retry_policy import ModelEffectRetryPolicy

__all__ = ["ModelEffectOperation"]


class ModelEffectOperation(BaseModel):
    """
    Single effect operation definition with discriminated union IO config.

    The `io_config` field uses a discriminated union based on `handler_type`.
    This ensures type-safe validation at contract load time.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Identity
    operation_name: str = Field(
        ..., min_length=1, max_length=EFFECT_OPERATION_NAME_MAX_LENGTH
    )
    description: str | None = Field(
        default=None, max_length=EFFECT_OPERATION_DESCRIPTION_MAX_LENGTH
    )

    # Idempotency - CRITICAL for retry safety
    idempotent: bool | None = Field(
        default=None,
        description="Override default idempotency. If None, uses handler/operation defaults.",
    )

    # Discriminated union IO config
    io_config: Annotated[
        ModelHttpIOConfig
        | ModelDbIOConfig
        | ModelKafkaIOConfig
        | ModelFilesystemIOConfig,
        Field(discriminator="handler_type"),
    ]

    # Response handling
    response_handling: ModelEffectResponseHandling = Field(
        default_factory=ModelEffectResponseHandling
    )

    # Resilience (can be overridden per-operation)
    retry_policy: ModelEffectRetryPolicy | None = None
    circuit_breaker: ModelEffectCircuitBreaker | None = None

    # Correlation
    correlation_id: UUID = Field(default_factory=uuid4)

    # Operation-level timeout (guards against retry stacking)
    operation_timeout_ms: int | None = Field(
        default=None,
        ge=EFFECT_TIMEOUT_MIN_MS,
        le=EFFECT_TIMEOUT_MAX_MS,
        description="Overall operation timeout including all retries. "
        "If None, defaults to TIMEOUT_DEFAULT_MS (30s). "
        "Prevents retry stacking from exceeding intended limits. "
        "See omnibase_core.constants for timeout constant values.",
    )

    @property
    def handler_type(self) -> str:
        """Extract handler type from IO config."""
        return str(self.io_config.handler_type.value)

    def get_effective_idempotency(self) -> bool:
        """
        Determine effective idempotency for this operation.

        Priority:
        1. Explicit `idempotent` field if set
        2. Default based on handler_type and operation
        """
        if self.idempotent is not None:
            return self.idempotent

        handler = str(self.io_config.handler_type.value)
        defaults: Mapping[str, bool] = IDEMPOTENCY_DEFAULTS.get(handler, {})

        # Extract operation type for lookup using match/case for type narrowing
        op_type: str
        match self.io_config:
            case ModelHttpIOConfig(method=method):
                op_type = method
            case ModelFilesystemIOConfig(operation=operation):
                op_type = operation
            case ModelKafkaIOConfig():
                op_type = "produce"
            case ModelDbIOConfig(operation=operation):
                op_type = operation.upper()
                # 'raw' operations default to non-idempotent for safety
                if op_type == "RAW":
                    return False
            case _:  # Defensive: unknown handler types default to non-idempotent
                return False  # type: ignore[unreachable]  # Safety-first: prevent accidental retries of unknown operations

        return defaults.get(
            op_type, False
        )  # Safety-first: unknown operations are non-idempotent
