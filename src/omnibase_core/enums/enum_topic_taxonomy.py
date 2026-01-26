"""
Topic Taxonomy Enums for ONEX Domain Topic Configuration.

Defines the enumeration types for topic categories and cleanup policies
per OMN-939 topic taxonomy specification.

Thread Safety:
    All enums in this module are immutable and thread-safe.
    Enum values can be safely shared across threads without synchronization.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumTopicType(StrValueHelper, str, Enum):
    """
    Valid topic types per ONEX topic taxonomy.

    Defines the standard topic categories used across all ONEX domains:
    - COMMANDS: Request/action topics (imperative, exactly-once semantics)
    - EVENTS: Immutable event logs (append-only, time-based retention)
    - INTENTS: Intent coordination topics (workflow orchestration)
    - SNAPSHOTS: State snapshots (compacted, key-based retention)
    - DLQ: Dead letter queue topics (failed message storage)
    """

    COMMANDS = "commands"
    DLQ = "dlq"
    EVENTS = "events"
    INTENTS = "intents"
    SNAPSHOTS = "snapshots"


@unique
class EnumCleanupPolicy(StrValueHelper, str, Enum):
    """
    Kafka cleanup policies for topic log management.

    - DELETE: Time/size-based log segment deletion
    - COMPACT: Key-based compaction (keeps latest per key)
    - COMPACT_DELETE: Hybrid - compact then delete old segments
    """

    DELETE = "delete"
    COMPACT = "compact"
    COMPACT_DELETE = "compact,delete"


__all__ = [
    "EnumCleanupPolicy",
    "EnumTopicType",
]
