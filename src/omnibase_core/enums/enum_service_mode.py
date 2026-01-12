"""
Service deployment modes enum.
"""

from enum import Enum, unique


@unique
class EnumServiceMode(str, Enum):
    """Service deployment modes."""

    STANDALONE = "standalone"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    COMPOSE = "compose"
