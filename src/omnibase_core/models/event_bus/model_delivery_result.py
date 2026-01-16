"""Delivery result model for event bus message publishing confirmation.

Thread Safety:
    ModelDeliveryResult instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.constants.constants_field_limits import MAX_NAME_LENGTH


class ModelDeliveryResult(BaseModel):
    """
    Delivery confirmation result for event bus message publishing.

    Represents the outcome of a message publish operation including
    success/failure status, topic, partition, offset, and timestamp.

    Attributes:
        success: Whether the message was successfully delivered.
        topic: Topic the message was published to.
        partition: Partition the message was written to.
        offset: Offset of the message within the partition.
        timestamp: Timestamp when the message was accepted by the broker.
        error_message: Error message if delivery failed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    success: bool = Field(
        ...,
        description="Whether the message was successfully delivered",
    )
    topic: str = Field(
        ...,
        description="Topic the message was published to",
        min_length=1,
        max_length=MAX_NAME_LENGTH,
    )
    partition: int | None = Field(
        default=None,
        description="Partition the message was written to",
        ge=0,
    )
    offset: int | None = Field(
        default=None,
        description="Offset of the message within the partition",
        ge=0,
    )
    timestamp: datetime | None = Field(
        default=None,
        description="Timestamp when the message was accepted by the broker",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if delivery failed",
        max_length=2000,
    )

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        """Validate topic name format."""
        v = v.strip()
        if not v:
            msg = "topic cannot be empty or whitespace"
            raise ValueError(msg)
        return v

    @field_validator("error_message")
    @classmethod
    def validate_error_message(cls, v: str | None) -> str | None:
        """Strip whitespace from error message."""
        if v is None:
            return None
        v = v.strip()
        return v if v else None

    def is_successful(self) -> bool:
        """Check if the delivery was successful."""
        return self.success

    def is_failed(self) -> bool:
        """Check if the delivery failed."""
        return not self.success

    def has_offset(self) -> bool:
        """Check if offset is available (indicates successful write)."""
        return self.offset is not None

    def has_timestamp(self) -> bool:
        """Check if timestamp is available."""
        return self.timestamp is not None

    def has_error(self) -> bool:
        """Check if there is an error message."""
        return self.error_message is not None and len(self.error_message) > 0

    def get_partition_offset(self) -> str:
        """Get formatted partition:offset string."""
        if self.partition is None or self.offset is None:
            return "unknown"
        return f"{self.partition}:{self.offset}"

    def get_timestamp_iso(self) -> str | None:
        """Get timestamp as ISO format string."""
        if self.timestamp is None:
            return None
        return self.timestamp.isoformat()

    def get_summary(self) -> str:
        """Get human-readable summary of the delivery result."""
        if self.success:
            return f"Delivered to {self.topic}[{self.get_partition_offset()}]"
        return f"Failed to deliver to {self.topic}: {self.error_message or 'Unknown error'}"

    @classmethod
    def create_success(
        cls,
        topic: str,
        partition: int,
        offset: int,
        timestamp: datetime | None = None,
    ) -> "ModelDeliveryResult":
        """Create a successful delivery result."""
        return cls(
            success=True,
            topic=topic,
            partition=partition,
            offset=offset,
            timestamp=timestamp or datetime.now(UTC),
        )

    @classmethod
    def create_failure(
        cls,
        topic: str,
        error_message: str,
        partition: int | None = None,
    ) -> "ModelDeliveryResult":
        """Create a failed delivery result."""
        return cls(
            success=False,
            topic=topic,
            partition=partition,
            offset=None,
            timestamp=None,
            error_message=error_message,
        )


__all__ = ["ModelDeliveryResult"]
