# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Whether validation completed or produced a terminal failure."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumModelSwapValidationStatus(UtilStrValueHelper, str, Enum):
    """Whether validation completed or produced a terminal failure."""

    COMPLETED = "completed"
    FAILED = "failed"


__all__ = ["EnumModelSwapValidationStatus"]
