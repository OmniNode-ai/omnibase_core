"""Artifact type enumeration for ONEX core."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumArtifactType(StrValueHelper, str, Enum):
    """Artifact types for ONEX ecosystem."""

    TOOL = "tool"
    VALIDATOR = "validator"
    AGENT = "agent"
    MODEL = "model"
    PLUGIN = "plugin"
    SCHEMA = "schema"
    CONFIG = "config"


__all__ = ["EnumArtifactType"]
