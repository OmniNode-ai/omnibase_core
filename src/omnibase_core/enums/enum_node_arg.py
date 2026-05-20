# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumNodeArg(UtilStrValueHelper, str, Enum):
    """
    Canonical enum for node argument types.
    """

    ARGS = "args"
    KWARGS = "kwargs"
    INPUT_STATE = "input_state"
    CONFIG = "config"

    BOOTSTRAP = "--bootstrap"
    HEALTH_CHECK = "--health-check"
    INTROSPECT = "--introspect"


__all__ = ["EnumNodeArg"]
