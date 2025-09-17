"""
Service deployment modes enum.
"""

from enum import Enum


class ModelServiceModeEnum(str, Enum):
    """Service deployment modes."""

    STANDALONE = "standalone"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    COMPOSE = "compose"
