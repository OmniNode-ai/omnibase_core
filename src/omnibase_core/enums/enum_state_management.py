# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
State Management Enums.

Comprehensive enum definitions for state management functionality including
storage backends, consistency levels, conflict resolution, versioning,
scoping, lifecycle, locking, isolation, and encryption options.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumStorageBackend(UtilStrValueHelper, str, Enum):
    """Storage backend options for state persistence."""

    POSTGRESQL = "postgresql"
    REDIS = "redis"
    MEMORY = "memory"
    FILE_SYSTEM = "file_system"


@unique
class EnumConsistencyLevel(UtilStrValueHelper, str, Enum):
    """Consistency levels for distributed state management."""

    EVENTUAL = "eventual"
    STRONG = "strong"
    WEAK = "weak"
    CAUSAL = "causal"


@unique
class EnumConflictResolution(UtilStrValueHelper, str, Enum):
    """Conflict resolution strategies."""

    TIMESTAMP_BASED = "timestamp_based"
    LAST_WRITE_WINS = "last_write_wins"
    MANUAL_RESOLUTION = "manual_resolution"
    MERGE_STRATEGY = "merge_strategy"


@unique
class EnumVersionScheme(UtilStrValueHelper, str, Enum):
    """State versioning schemes."""

    SEMANTIC = "semantic"
    INCREMENTAL = "incremental"
    TIMESTAMP = "timestamp"
    UUID_BASED = "uuid_based"


@unique
class EnumStateScope(UtilStrValueHelper, str, Enum):
    """State management scope options."""

    NODE_LOCAL = "node_local"
    CLUSTER_SHARED = "cluster_shared"
    GLOBAL_DISTRIBUTED = "global_distributed"


@unique
class EnumStateLifecycle(UtilStrValueHelper, str, Enum):
    """State lifecycle management strategies."""

    PERSISTENT = "persistent"
    TRANSIENT = "transient"
    SESSION_BASED = "session_based"
    TTL_MANAGED = "ttl_managed"


@unique
class EnumLockingStrategy(UtilStrValueHelper, str, Enum):
    """Locking strategies for state access."""

    OPTIMISTIC = "optimistic"
    PESSIMISTIC = "pessimistic"
    READ_WRITE_LOCKS = "read_write_locks"
    NONE = "none"


@unique
class EnumIsolationLevel(UtilStrValueHelper, str, Enum):
    """Transaction isolation levels."""

    READ_UNCOMMITTED = "read_uncommitted"
    READ_COMMITTED = "read_committed"
    REPEATABLE_READ = "repeatable_read"
    SERIALIZABLE = "serializable"


@unique
class EnumEncryptionAlgorithm(UtilStrValueHelper, str, Enum):
    """Encryption algorithms for state data."""

    AES256 = "aes256"
    AES128 = "aes128"
    CHACHA20 = "chacha20"
    NONE = "none"


__all__ = [
    "EnumConsistencyLevel",
    "EnumConflictResolution",
    "EnumEncryptionAlgorithm",
    "EnumIsolationLevel",
    "EnumLockingStrategy",
    "EnumStateLifecycle",
    "EnumStateScope",
    "EnumStorageBackend",
    "EnumVersionScheme",
]
