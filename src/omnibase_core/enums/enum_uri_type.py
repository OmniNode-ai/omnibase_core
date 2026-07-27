# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
URI type enum for ONEX URI classification.

Defines the valid types for ONEX URIs as referenced in
node contracts and structural conventions.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumUriType(UtilStrValueHelper, str, Enum):
    """Valid types for ONEX URIs."""

    TOOL = "tool"
    VALIDATOR = "validator"
    AGENT = "agent"
    MODEL = "model"
    PLUGIN = "plugin"
    SCHEMA = "schema"
    NODE = "node"


__all__ = ["EnumUriType"]
