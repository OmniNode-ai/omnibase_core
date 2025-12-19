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
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

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
        Short retention (24h) since commands are processed promptly.
        """
        return cls(
            topic_type=EnumTopicType.COMMANDS,
            cleanup_policy=EnumCleanupPolicy.DELETE,
            retention_ms=86400000,  # 24 hours
            partitions=3,
            replication_factor=1,
        )

    @classmethod
    def events_default(cls) -> "ModelTopicConfig":
        """
        Default configuration for events topics.

        Events are immutable logs of domain state changes.
        Longer retention (7 days) for replay and audit purposes.
        """
        return cls(
            topic_type=EnumTopicType.EVENTS,
            cleanup_policy=EnumCleanupPolicy.DELETE,
            retention_ms=604800000,  # 7 days
            partitions=3,
            replication_factor=1,
        )

    @classmethod
    def intents_default(cls) -> "ModelTopicConfig":
        """
        Default configuration for intents topics.

        Intents coordinate workflow actions between nodes.
        Medium retention (48h) for retry and recovery.
        """
        return cls(
            topic_type=EnumTopicType.INTENTS,
            cleanup_policy=EnumCleanupPolicy.DELETE,
            retention_ms=172800000,  # 48 hours
            partitions=3,
            replication_factor=1,
        )

    @classmethod
    def snapshots_default(cls) -> "ModelTopicConfig":
        """
        Default configuration for snapshots topics.

        Snapshots store latest state per entity key.
        Compacted to retain only the most recent value per key.
        """
        return cls(
            topic_type=EnumTopicType.SNAPSHOTS,
            cleanup_policy=EnumCleanupPolicy.COMPACT_DELETE,
            retention_ms=None,  # Indefinite for compacted topics
            partitions=3,
            replication_factor=1,
        )


__all__ = [
    "ModelTopicConfig",
]
