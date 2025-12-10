"""
State Management Enums.

Comprehensive enum definitions for state management functionality including
storage backends, consistency levels, conflict resolution, versioning,
scoping, lifecycle, locking, isolation, and encryption options.
"""

from enum import Enum


class EnumStorageBackend(str, Enum):
    """Storage backend options for state persistence."""

    POSTGRESQL = "postgresql"
    REDIS = "redis"
    MEMORY = "memory"
    FILE_SYSTEM = "file_system"


class EnumConsistencyLevel(str, Enum):
    """Consistency levels for distributed state management."""

    EVENTUAL = "eventual"
    STRONG = "strong"
    WEAK = "weak"
    CAUSAL = "causal"


class EnumConflictResolution(str, Enum):
    """Conflict resolution strategies."""

    TIMESTAMP_BASED = "timestamp_based"
    LAST_WRITE_WINS = "last_write_wins"
    MANUAL_RESOLUTION = "manual_resolution"
    MERGE_STRATEGY = "merge_strategy"


class EnumVersionScheme(str, Enum):
    """State versioning schemes."""

    SEMANTIC = "semantic"
    INCREMENTAL = "incremental"
    TIMESTAMP = "timestamp"
    UUID_BASED = "uuid_based"


class EnumStateScope(str, Enum):
    """State management scope options."""

    NODE_LOCAL = "node_local"
    CLUSTER_SHARED = "cluster_shared"
    GLOBAL_DISTRIBUTED = "global_distributed"


class EnumStateLifecycle(str, Enum):
    """State lifecycle management strategies."""

    PERSISTENT = "persistent"
    TRANSIENT = "transient"
    SESSION_BASED = "session_based"
    TTL_MANAGED = "ttl_managed"


class EnumLockingStrategy(str, Enum):
    """Locking strategies for state access."""

    OPTIMISTIC = "optimistic"
    PESSIMISTIC = "pessimistic"
    READ_WRITE_LOCKS = "read_write_locks"
    NONE = "none"


class EnumIsolationLevel(str, Enum):
    """Transaction isolation levels."""

    READ_UNCOMMITTED = "read_uncommitted"
    READ_COMMITTED = "read_committed"
    REPEATABLE_READ = "repeatable_read"
    SERIALIZABLE = "serializable"


class EnumEncryptionAlgorithm(str, Enum):
    """Encryption algorithms for state data."""

    AES256 = "aes256"
    AES128 = "aes128"
    CHACHA20 = "chacha20"
    NONE = "none"
