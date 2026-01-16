"""
Kafka IO Configuration Model.

Provides Kafka message production configuration with topic, payload templating,
partition key generation, and delivery settings.

WARNING: Using acks="0" (fire-and-forget) provides no delivery guarantees
and messages may be lost silently. This configuration requires explicit
opt-in via the acks_zero_acknowledged field.

Thread Safety:
    This model is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access.

See Also:
    - :class:`ModelEffectSubcontract`: Parent contract using this IO config
    - :class:`NodeEffect`: The primary node using this configuration
    - docs/architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md: Full specification

Author: ONEX Framework Team
"""

import warnings
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.constants.constants_effect_limits import (
    EFFECT_TIMEOUT_DEFAULT_MS,
    EFFECT_TIMEOUT_MAX_MS,
    EFFECT_TIMEOUT_MIN_MS,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError

__all__ = [
    "ModelKafkaIOConfig",
]


class ModelKafkaIOConfig(BaseModel):
    """
    Kafka IO configuration for message production.

    Provides topic configuration, payload templating, partition key generation,
    and delivery settings for Kafka message production.

    WARNING: Using acks="0" (fire-and-forget) provides no delivery guarantees
    and messages may be lost silently. This configuration requires explicit
    opt-in via the acks_zero_acknowledged field.

    Attributes:
        handler_type: Discriminator field identifying this as a Kafka handler.
        topic: Kafka topic to produce messages to.
        payload_template: Message payload template with ${} placeholders.
        partition_key_template: Template for partition key (affects message ordering).
        headers: Kafka message headers with optional ${} placeholders.
        timeout_ms: Producer timeout in milliseconds (1s - 10min).
        acks: Acknowledgment level (0=none, 1=leader, all=all replicas).
        acks_zero_acknowledged: Explicit opt-in for acks=0 mode.
        compression: Compression codec for message payloads.

    Example:
        >>> config = ModelKafkaIOConfig(
        ...     topic="user-events",
        ...     payload_template='{"user_id": "${input.user_id}", "action": "${input.action}"}',
        ...     partition_key_template="${input.user_id}",
        ...     acks="all",
        ... )

    Example with acks=0 (fire-and-forget, use with caution):
        >>> config = ModelKafkaIOConfig(
        ...     topic="metrics",
        ...     payload_template='{"metric": "${input.name}", "value": ${input.value}}',
        ...     acks="0",
        ...     acks_zero_acknowledged=True,  # Required explicit opt-in
        ... )
    """

    handler_type: Literal[EnumEffectHandlerType.KAFKA] = Field(
        default=EnumEffectHandlerType.KAFKA,
        description="Discriminator field for Kafka handler",
    )

    topic: str = Field(
        ...,
        description="Kafka topic to produce messages to",
        min_length=1,
    )

    payload_template: str = Field(
        ...,
        description="Message payload template with ${} placeholders",
        min_length=1,
    )

    partition_key_template: str | None = Field(
        default=None,
        description="Template for partition key (affects message ordering)",
    )

    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Kafka message headers with optional ${} placeholders",
    )

    timeout_ms: int = Field(
        default=EFFECT_TIMEOUT_DEFAULT_MS,
        ge=EFFECT_TIMEOUT_MIN_MS,
        le=EFFECT_TIMEOUT_MAX_MS,
        description="Producer timeout in milliseconds (1s - 10min)",
    )

    acks: Literal["0", "1", "all"] = Field(
        default="all",
        description="Acknowledgment level: 0=none (fire-and-forget, may lose messages), "
        "1=leader only, all=all replicas (strongest guarantee)",
    )

    acks_zero_acknowledged: bool = Field(
        default=False,
        description="Explicit opt-in for acks=0 (fire-and-forget mode). "
        "Must be True when using acks='0' to acknowledge the risk of message loss.",
    )

    compression: Literal["none", "gzip", "snappy", "lz4", "zstd"] = Field(
        default="none",
        description="Compression codec for message payloads",
    )

    @model_validator(mode="after")
    def validate_acks_zero_opt_in(self) -> "ModelKafkaIOConfig":
        """
        Require explicit opt-in for acks=0 configuration.

        Kafka acks=0 (fire-and-forget) provides no delivery guarantees and messages
        may be lost silently. This validator ensures users explicitly acknowledge
        this risk by setting acks_zero_acknowledged=True.

        Returns:
            The validated model instance.

        Raises:
            ModelOnexError: If acks=0 without acks_zero_acknowledged=True.
        """
        if self.acks == "0":
            # Always emit a warning when acks=0 is used
            warnings.warn(
                "Kafka acks=0 provides no delivery guarantees. Messages may be lost. "
                "Use acks=1 or acks='all' for better reliability.",
                UserWarning,
                stacklevel=2,
            )
            # Require explicit opt-in
            if not self.acks_zero_acknowledged:
                raise ModelOnexError(
                    message="Kafka acks=0 requires explicit opt-in. "
                    "Set acks_zero_acknowledged=True to acknowledge the risk of message loss.",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "acks_zero_opt_in"
                            ),
                            "acks": ModelSchemaValue.from_value(self.acks),
                            "acks_zero_acknowledged": ModelSchemaValue.from_value(
                                self.acks_zero_acknowledged
                            ),
                        }
                    ),
                )
        return self

    @model_validator(mode="after")
    def validate_acks_zero_acknowledged_only_for_acks_zero(
        self,
    ) -> "ModelKafkaIOConfig":
        """
        Prevent acks_zero_acknowledged=True when acks is not "0".

        The acks_zero_acknowledged field is only meaningful when acks="0".
        Setting it to True with acks="1" or acks="all" is a configuration error
        that creates confusing state. This validator ensures consistent configuration.

        Returns:
            The validated model instance.

        Raises:
            ModelOnexError: If acks_zero_acknowledged=True with acks != "0".
        """
        if self.acks != "0" and self.acks_zero_acknowledged:
            raise ModelOnexError(
                message=f"acks_zero_acknowledged=True is only valid when acks='0', "
                f"but acks='{self.acks}'. Set acks_zero_acknowledged=False or "
                f"change acks to '0'.",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "acks_zero_acknowledged_semantics"
                        ),
                        "acks": ModelSchemaValue.from_value(self.acks),
                        "acks_zero_acknowledged": ModelSchemaValue.from_value(
                            self.acks_zero_acknowledged
                        ),
                    }
                ),
            )
        return self

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
