"""
EnumScalabilityLevel: Enumeration of scalability levels.

This enum defines the scalability levels for performance profiles.
"""

from enum import Enum


class EnumScalabilityLevel(Enum):
    """Scalability levels for performance profiles."""

    LIMITED = "limited"
    GOOD = "good"
    EXCELLENT = "excellent"
