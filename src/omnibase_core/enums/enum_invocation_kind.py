# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumInvocationKind(UtilStrValueHelper, str, Enum):
    """Routing axis distinguishing remote-agent invocations from raw-model invocations."""

    AGENT = "agent"
    MODEL = "model"


__all__ = ["EnumInvocationKind"]
