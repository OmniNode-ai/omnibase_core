"""
Artifact Type Enum.

Strongly typed artifact type values for configuration.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class EnumArtifactType(str, Enum):
    """Strongly typed artifact type values."""

    TOOL = "tool"
    VALIDATOR = "validator"
    AGENT = "agent"
    MODEL = "model"
    PLUGIN = "plugin"
    SCHEMA = "schema"
    CONFIG = "config"


# Export for use
__all__ = ["EnumArtifactType"]
