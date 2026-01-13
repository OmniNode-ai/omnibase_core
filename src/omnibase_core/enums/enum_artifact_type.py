"""Artifact type enumeration for ONEX core."""

from enum import Enum, unique


@unique
class EnumArtifactType(str, Enum):
    """Artifact types for ONEX ecosystem."""

    TOOL = "tool"
    VALIDATOR = "validator"
    AGENT = "agent"
    MODEL = "model"
    PLUGIN = "plugin"
    SCHEMA = "schema"
    CONFIG = "config"
