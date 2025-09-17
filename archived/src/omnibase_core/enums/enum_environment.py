"""
Enum for environment types.
"""

from enum import Enum


class EnumEnvironment(str, Enum):
    """Environment types for ONEX systems."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"
    LOCAL = "local"
    CI = "ci"
