# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Channel type classification for OmniClaw messaging platforms."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumChannelType(StrValueHelper, str, Enum):
    """Messaging platform type for OmniClaw channel adapters.

    Identifies the external messaging platform from which a message
    originated or to which a reply should be dispatched.
    """

    DISCORD = "discord"
    SLACK = "slack"
    TELEGRAM = "telegram"
    EMAIL = "email"
    SMS = "sms"
    MATRIX = "matrix"


__all__ = ["EnumChannelType"]
