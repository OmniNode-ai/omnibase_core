"""
Node registration status enumeration.

Provides strongly typed registration status values for ONEX nodes.
"""

from enum import Enum


class EnumNodeRegistrationStatus(str, Enum):
    """Status of node registration."""

    REGISTERED = "registered"
    PENDING = "pending"
    FAILED = "failed"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"
