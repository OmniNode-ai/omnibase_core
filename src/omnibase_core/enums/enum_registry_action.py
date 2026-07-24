# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Node registry actions for ONEX operations."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumRegistryAction(UtilStrValueHelper, str, Enum):
    """Registry actions for node operations."""

    GET_ACTIVE_NODES = "get_active_nodes"
    GET_NODE = "get_node"
