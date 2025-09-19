"""
Storage type enum for node configurations.
"""

from enum import Enum


class EnumStorageType(str, Enum):
    """Supported storage types for node configurations."""

    MEMORY = "memory"
    DISK = "disk"
    DATABASE = "database"
    REDIS = "redis"
    FILE = "file"
    S3 = "s3"
    CLOUD = "cloud"
