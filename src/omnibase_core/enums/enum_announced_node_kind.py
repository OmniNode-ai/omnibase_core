# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Kind of an announced entry (OMN-21589)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumAnnouncedNodeKind(UtilStrValueHelper, str, Enum):
    """Kind of entry a package announces.

    Attributes:
        NODE: An ordinary node contract.
        KERNEL_PLUGIN: A kernel plugin, enabled by name in the lane overlay.
    """

    NODE = "node"
    KERNEL_PLUGIN = "kernel_plugin"
