"""
URI type enum for ONEX URI classification.

Defines the valid types for ONEX URIs as referenced in
node contracts and structural conventions.
"""

from enum import Enum


class EnumUriType(str, Enum):
    """Valid types for ONEX URIs."""

    TOOL = "tool"
    VALIDATOR = "validator"
    AGENT = "agent"
    MODEL = "model"
    PLUGIN = "plugin"
    SCHEMA = "schema"
    NODE = "node"
