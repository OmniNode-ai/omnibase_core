# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Which side of a guardrail bound is acceptable (OMN-22001)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumGuardrailDirection(UtilStrValueHelper, str, Enum):
    """Direction of a guardrail comparison.

    Attributes:
        AT_MOST: The measured value must not exceed the bound.
        AT_LEAST: The measured value must reach the bound.
    """

    AT_MOST = "at_most"
    AT_LEAST = "at_least"
