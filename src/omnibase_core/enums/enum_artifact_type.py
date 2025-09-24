"""
Artifact Type Enum.

Strongly typed artifact type values for configuration.
"""

from __future__ import annotations

from enum import Enum


class EnumArtifactType(str, Enum):
    """Strongly typed artifact type values."""

    TOOL = "TOOL"
    VALIDATOR = "validator"
    AGENT = "AGENT"
    MODEL = "MODEL"
    PLUGIN = "plugin"
    SCHEMA = "schema"
    CONFIG = "config"


# Export for use
__all__ = ["EnumArtifactType"]
