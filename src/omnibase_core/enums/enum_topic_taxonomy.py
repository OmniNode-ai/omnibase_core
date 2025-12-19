"""
Topic Taxonomy Enums for ONEX Domain Topic Configuration.

Defines the enumeration types for topic categories and cleanup policies
per OMN-939 topic taxonomy specification.
"""

from enum import Enum, unique


@unique
class EnumTopicType(str, Enum):
    """
    Valid topic types per ONEX topic taxonomy.

    Defines the four standard topic categories used across all ONEX domains:
    - COMMANDS: Request/action topics (imperative, exactly-once semantics)
    - EVENTS: Immutable event logs (append-only, time-based retention)
    - INTENTS: Intent coordination topics (workflow orchestration)
    - SNAPSHOTS: State snapshots (compacted, key-based retention)
    """

    COMMANDS = "commands"
    EVENTS = "events"
    INTENTS = "intents"
    SNAPSHOTS = "snapshots"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value


@unique
class EnumCleanupPolicy(str, Enum):
    """
    Kafka cleanup policies for topic log management.

    - DELETE: Time/size-based log segment deletion
    - COMPACT: Key-based compaction (keeps latest per key)
    - COMPACT_DELETE: Hybrid - compact then delete old segments
    """

    DELETE = "delete"
    COMPACT = "compact"
    COMPACT_DELETE = "compact,delete"

    def __str__(self) -> str:
        """Return the string value for Kafka configuration."""
        return self.value


__all__ = [
    "EnumCleanupPolicy",
    "EnumTopicType",
]
