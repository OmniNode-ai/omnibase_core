"""
Artifact Type Enum.

Strongly typed artifact type values for configuration.
"""

from __future__ import annotations

from enum import Enum


class EnumArtifactType(str, Enum):
    """Strongly typed artifact type values."""

    TOOL = "TOOL"
    VALIDATOR = "VALIDATOR"
    AGENT = "AGENT"
    MODEL = "MODEL"
    PLUGIN = "PLUGIN"
    SCHEMA = "SCHEMA"
    CONFIG = "CONFIG"


# Export for use
__all__ = ["EnumArtifactType"]
