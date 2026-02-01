"""
Topic Configuration Model for ONEX Domain Topics.

Defines the per-topic configuration including retention, compaction,
partitioning, and replication settings per OMN-939 topic taxonomy.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_topic_taxonomy import (
    EnumCleanupPolicy,
    EnumTopicType,
)


class ModelTopicConfig(BaseModel):
    """
    Configuration for a single Kafka topic.

    Defines retention, compaction, partitioning, and replication
    settings for domain topics in the ONEX framework.

    Thread Safety:
        This model is immutable (frozen=True) and thread-safe after instantiation.
        Instances can be safely shared across threads without synchronization.

    See Also:
        - docs/standards/onex_topic_taxonomy.md for retention defaults
        - docs/guides/THREADING.md for thread safety guidelines
    """

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    topic_type: EnumTopicType = Field(
        ...,
        description="Topic type category (commands, events, intents, snapshots)",
    )
    cleanup_policy: EnumCleanupPolicy = Field(
        ...,
        description="Kafka cleanup policy for log management",
    )
    retention_ms: int | None = Field(
        default=None,
        ge=0,
        description="Retention period in milliseconds (None = broker default)",
    )
    retention_bytes: int | None = Field(
        default=None,
        ge=-1,
        description="Retention size in bytes (-1 = unlimited, None = broker default)",
    )
    partitions: int = Field(
        default=3,
        ge=1,
        le=1000,
        description="Number of partitions for parallel processing",
    )
    replication_factor: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Replication factor for fault tolerance",
    )

    @classmethod
    def commands_default(cls) -> "ModelTopicConfig":
        """
        Default configuration for commands topics.

        Commands are imperative requests that require exactly-once processing.
        Default retention is 7 days per ONEX topic taxonomy standard.

        Note:
            This model is immutable (frozen) and thread-safe after instantiation.
        """
        return cls(
            topic_type=EnumTopicType.COMMANDS,
            cleanup_policy=EnumCleanupPolicy.DELETE,
            retention_ms=604800000,  # 7 days per ONEX standard
            partitions=3,
            replication_factor=1,
        )

    @classmethod
    def events_default(cls) -> "ModelTopicConfig":
        """
        Default configuration for events topics.

        Events are immutable logs of domain state changes.
        Default retention is 30 days for replay and audit purposes per ONEX standard.

        Note:
            This model is immutable (frozen) and thread-safe after instantiation.
        """
        return cls(
            topic_type=EnumTopicType.EVENTS,
            cleanup_policy=EnumCleanupPolicy.DELETE,
            retention_ms=2592000000,  # 30 days per ONEX standard
            partitions=3,
            replication_factor=1,
        )

    @classmethod
    def intents_default(cls) -> "ModelTopicConfig":
        """
        Default configuration for intents topics.

        Intents coordinate workflow actions between nodes.
        Default retention is 1 day for short-lived coordination per ONEX standard.

        Note:
            This model is immutable (frozen) and thread-safe after instantiation.
        """
        return cls(
            topic_type=EnumTopicType.INTENTS,
            cleanup_policy=EnumCleanupPolicy.DELETE,
            retention_ms=86400000,  # 1 day per ONEX standard
            partitions=3,
            replication_factor=1,
        )

    @classmethod
    def snapshots_default(cls) -> "ModelTopicConfig":
        """
        Default configuration for snapshots topics.

        Snapshots store latest state per entity key.
        Compacted to retain only the most recent value per key.
        Default retention is 7 days per ONEX standard.

        Note:
            This model is immutable (frozen) and thread-safe after instantiation.
        """
        return cls(
            topic_type=EnumTopicType.SNAPSHOTS,
            cleanup_policy=EnumCleanupPolicy.COMPACT_DELETE,
            retention_ms=604800000,  # 7 days per ONEX standard
            partitions=3,
            replication_factor=1,
        )

    @classmethod
    def dlq_default(cls) -> "ModelTopicConfig":
        """
        Default configuration for dead letter queue (DLQ) topics.

        DLQ topics store failed messages for investigation and retry.
        Default retention is 30 days per ONEX standard (same as events for audit).

        Note:
            This model is immutable (frozen) and thread-safe after instantiation.
        """
        return cls(
            topic_type=EnumTopicType.DLQ,
            cleanup_policy=EnumCleanupPolicy.DELETE,
            retention_ms=2592000000,  # 30 days per ONEX standard
            partitions=3,
            replication_factor=1,
        )


__all__ = [
    "ModelTopicConfig",
]
