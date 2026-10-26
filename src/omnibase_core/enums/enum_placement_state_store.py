# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Durable state stores supported by runtime placement."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumPlacementStateStore(UtilStrValueHelper, str, Enum):
    """Where a node's state can be recovered after primary failover."""

    PROJECTION = "projection"
    NONE = "none"
    LEASE_STORE = "lease_store"
