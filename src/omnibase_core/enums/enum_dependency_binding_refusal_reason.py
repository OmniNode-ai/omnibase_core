# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed reasons a handler's dependencies could not be built from the overlay (OMN-21595)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumDependencyBindingRefusalReason(UtilStrValueHelper, str, Enum):
    """Why a contract's handler dependencies were refused before anything was built.

    Attributes:
        DEPENDENCY_UNBOUND: The contract declares a protocol the lane overlay does not bind.
        IMPLEMENTATION_NOT_REGISTERED: The overlay binds a protocol to an implementation no
            factory is registered under.
    """

    DEPENDENCY_UNBOUND = "dependency_unbound"
    IMPLEMENTATION_NOT_REGISTERED = "implementation_not_registered"
