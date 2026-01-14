"""
URI type enum for ONEX URI classification.

Defines the valid types for ONEX URIs as referenced in
node contracts and structural conventions.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumUriType(StrValueHelper, str, Enum):
    """Valid types for ONEX URIs."""

    TOOL = "tool"
    VALIDATOR = "validator"
    AGENT = "agent"
    MODEL = "model"
    PLUGIN = "plugin"
    SCHEMA = "schema"
    NODE = "node"


__all__ = ["EnumUriType"]
