"""
Service deployment modes enum.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumServiceMode(StrValueHelper, str, Enum):
    """Service deployment modes."""

    STANDALONE = "standalone"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    COMPOSE = "compose"


__all__ = ["EnumServiceMode"]
