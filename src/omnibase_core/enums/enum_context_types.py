# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Context types for execution environment values."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumContextTypes(UtilStrValueHelper, str, Enum):
    """Enum for context types used in execution."""

    CONTEXT = "context"
    VARIABLE = "variable"
    ENVIRONMENT = "environment"
    CONFIGURATION = "configuration"
    RUNTIME = "runtime"


__all__ = ["EnumContextTypes"]
