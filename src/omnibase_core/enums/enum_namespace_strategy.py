# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Namespace strategy enumeration for ONEX framework.

Defines the available strategies for namespace handling in ONEX components.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumNamespaceStrategy(UtilStrValueHelper, str, Enum):
    """Enumeration of namespace strategies."""

    ONEX_DEFAULT = "onex_default"
    """Use ONEX default namespace strategy."""

    HIERARCHICAL = "hierarchical"
    """Use hierarchical namespace organization."""

    FLAT = "flat"
    """Use flat namespace organization."""

    CUSTOM = "custom"
    """Use custom namespace strategy."""


__all__ = ["EnumNamespaceStrategy"]
