"""
Service deployment modes enum.
"""

from enum import Enum


class EnumServiceMode(str, Enum):
    """Service deployment modes."""

    STANDALONE = "standalone"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    COMPOSE = "compose"
