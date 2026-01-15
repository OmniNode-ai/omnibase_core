"""
Resolved Kafka Context Model for NodeEffect Handler Contract.

This model represents a resolved (template-free) Kafka context that handlers receive
after template resolution by the effect executor.

Thread Safety:
    This model is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

See Also:
    - docs/architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md: Full specification
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants.constants_effect_limits import (
    EFFECT_TIMEOUT_DEFAULT_MS,
    EFFECT_TIMEOUT_MAX_MS,
    EFFECT_TIMEOUT_MIN_MS,
)
from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType


class ModelResolvedKafkaContext(BaseModel):
    """
    Resolved Kafka context for message queue operations.

    All template placeholders have been resolved by the effect executor.
    Message payload and headers are ready for immediate publishing.

    Attributes:
        handler_type: Discriminator field for Kafka handler type.
        topic: Kafka topic name.
        partition_key: Resolved partition key for message ordering.
        headers: Resolved Kafka message headers.
        payload: Fully resolved message payload.
        timeout_ms: Publish timeout in milliseconds (1s - 10min).
        acks: Acknowledgment level (0=none, 1=leader, all=all replicas).
        compression: Message compression algorithm.

    Example resolved values:
        - topic: "user-events" (was: "${KAFKA_TOPIC_PREFIX}-events")
        - payload: '{"user_id": 123}' (was: '{"user_id": ${user_id}}')
    """

    handler_type: Literal[EnumEffectHandlerType.KAFKA] = Field(
        default=EnumEffectHandlerType.KAFKA,
        description="Handler type discriminator for Kafka operations",
    )

    topic: str = Field(
        ...,
        min_length=1,
        description="Kafka topic name",
    )

    partition_key: str | None = Field(
        default=None,
        description="Resolved partition key for message ordering",
    )

    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Resolved Kafka message headers",
    )

    payload: str = Field(
        ...,
        description="Fully resolved message payload",
    )

    # Timeout bounds: 1s minimum (realistic production I/O), 10min maximum
    # Matches IO config timeout bounds for consistency across the effect layer
    timeout_ms: int = Field(
        default=EFFECT_TIMEOUT_DEFAULT_MS,
        ge=EFFECT_TIMEOUT_MIN_MS,
        le=EFFECT_TIMEOUT_MAX_MS,
        description="Publish timeout in milliseconds (1s - 10min)",
    )

    acks: Literal["0", "1", "all"] = Field(
        default="all",
        description="Acknowledgment level: 0=none, 1=leader, all=all replicas",
    )

    compression: Literal["none", "gzip", "snappy", "lz4", "zstd"] = Field(
        default="none",
        description="Message compression algorithm",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
    )
