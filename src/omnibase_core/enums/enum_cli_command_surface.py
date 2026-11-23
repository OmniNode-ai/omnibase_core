# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI command-group surface enum (OMN-26518)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumCliCommandSurface(UtilStrValueHelper, str, Enum):
    """Which audience an ``onex`` command group belongs to.

    Values:
        CUSTOMER: Listed in the default ``onex --help`` view and in shell
            completion; audited as part of the customer surface.
        INTERNAL: Hidden from the default view; listed and resolvable only
            with the operator switch on.
    """

    CUSTOMER = "customer"
    INTERNAL = "internal"


__all__ = ["EnumCliCommandSurface"]
