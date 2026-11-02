# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Role of a forwarded model request."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumModelSwapGatewayRole(UtilStrValueHelper, str, Enum):
    """Role of a forwarded model request."""

    CANDIDATE = "candidate"
    JUDGE = "judge"


__all__ = ["EnumModelSwapGatewayRole"]
