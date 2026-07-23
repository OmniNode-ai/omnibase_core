# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Enum for interface kind classifications.

Categorizes the type of interface a contract boundary represents,
used for ticket-driven interface tracking [OMN-1968].
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumInterfaceKind(UtilStrValueHelper, str, Enum):
    """Classification of interface types in contract boundaries."""

    PROTOCOL = "protocol"
    EVENT_SCHEMA = "event_schema"
    DATA_MODEL = "data_model"
    REST_ENDPOINT = "rest_endpoint"
    DATABASE_SCHEMA = "database_schema"
    CONFIG_SCHEMA = "config_schema"
    CLI_INTERFACE = "cli_interface"


# Alias for cleaner imports
InterfaceKind = EnumInterfaceKind

__all__ = [
    "EnumInterfaceKind",
    "InterfaceKind",
]
