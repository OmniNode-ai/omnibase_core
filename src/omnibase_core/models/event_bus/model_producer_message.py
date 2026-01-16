"""Producer message model for event bus message publishing.

Thread Safety:
    ModelProducerMessage instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.constants.constants_field_limits import MAX_NAME_LENGTH


class ModelProducerMessage(BaseModel):
    """
    Producer message structure for event bus publishing.

    Represents a message to be published to an event bus topic with
    optional partitioning, headers, and key-based routing.

    Attributes:
        topic: Target topic name for message publishing.
        value: Message payload as bytes.
        key: Optional message key for partitioning and ordering.
        headers: Optional message headers for metadata.
        partition: Optional specific partition number for targeted delivery.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    topic: str = Field(
        ...,
        description="Target topic name for message publishing",
        min_length=1,
        max_length=MAX_NAME_LENGTH,
    )
    value: bytes = Field(
        ...,
        description="Message payload as bytes",
    )
    key: bytes | None = Field(
        default=None,
        description="Optional message key for partitioning and ordering",
    )
    headers: dict[str, bytes] | None = Field(
        default=None,
        description="Optional message headers for metadata",
    )
    partition: int | None = Field(
        default=None,
        description="Optional specific partition number for targeted delivery",
        ge=0,
    )

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        """Validate topic name format."""
        v = v.strip()
        if not v:
            msg = "topic cannot be empty or whitespace"
            raise ValueError(msg)
        # Kafka topic naming constraints
        if not all(c.isalnum() or c in "._-" for c in v):
            msg = "topic must contain only alphanumeric characters, dots, underscores, or hyphens"
            raise ValueError(msg)
        return v

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: bytes) -> bytes:
        """Validate message value is not empty."""
        if not v:
            msg = "value cannot be empty"
            raise ValueError(msg)
        return v

    def get_key_string(self) -> str | None:
        """Get key as decoded string if present."""
        if self.key is None:
            return None
        return self.key.decode("utf-8", errors="replace")

    def get_value_string(self) -> str:
        """Get value as decoded string."""
        return self.value.decode("utf-8", errors="replace")

    def get_headers_dict(self) -> dict[str, str]:
        """Get headers as decoded string dictionary."""
        if self.headers is None:
            return {}
        return {k: v.decode("utf-8", errors="replace") for k, v in self.headers.items()}

    def has_key(self) -> bool:
        """Check if message has a key."""
        return self.key is not None

    def has_headers(self) -> bool:
        """Check if message has headers."""
        return self.headers is not None and len(self.headers) > 0

    def has_partition(self) -> bool:
        """Check if message has a specific partition."""
        return self.partition is not None

    def get_size_bytes(self) -> int:
        """Get total message size in bytes."""
        size = len(self.value)
        if self.key:
            size += len(self.key)
        if self.headers:
            for k, v in self.headers.items():
                size += len(k.encode("utf-8")) + len(v)
        return size

    @classmethod
    def create_simple(cls, topic: str, value: str) -> "ModelProducerMessage":
        """Create a simple message with string value."""
        return cls(topic=topic, value=value.encode("utf-8"))

    @classmethod
    def create_with_key(
        cls, topic: str, value: str, key: str
    ) -> "ModelProducerMessage":
        """Create a message with string key and value."""
        return cls(
            topic=topic,
            value=value.encode("utf-8"),
            key=key.encode("utf-8"),
        )

    @classmethod
    def create_with_headers(
        cls, topic: str, value: str, headers: dict[str, str]
    ) -> "ModelProducerMessage":
        """Create a message with headers."""
        return cls(
            topic=topic,
            value=value.encode("utf-8"),
            headers={k: v.encode("utf-8") for k, v in headers.items()},
        )


__all__ = ["ModelProducerMessage"]
