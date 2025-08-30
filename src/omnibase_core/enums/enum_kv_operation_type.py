"""
KV Operation Type Enum.

Canonical enum for key-value store operations used throughout ONEX
Consul integration and distributed storage systems.
"""

from enum import Enum


class EnumKVOperationType(str, Enum):
    """Canonical KV operation types for ONEX distributed storage."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    WATCH = "watch"
    SYNC = "sync"
    BACKUP = "backup"
    RESTORE = "restore"
