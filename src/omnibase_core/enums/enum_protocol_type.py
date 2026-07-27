# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Protocol Type Enum.

Defines communication protocols for node configurations.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumProtocolType(UtilStrValueHelper, str, Enum):
    """Communication protocol types."""

    HTTP = "http"
    HTTPS = "https"
    TCP = "tcp"
    UDP = "udp"
    WEBSOCKET = "websocket"
    GRPC = "grpc"
    REST = "rest"
    GRAPHQL = "graphql"


# Export for use
__all__ = ["EnumProtocolType"]
