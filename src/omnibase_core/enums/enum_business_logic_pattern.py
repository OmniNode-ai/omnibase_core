# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Business logic pattern classifications for node categorization."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumBusinessLogicPattern(UtilStrValueHelper, str, Enum):
    """Business logic pattern classifications."""

    STATELESS = "stateless"
    STATEFUL = "stateful"
    COORDINATION = "coordination"
    AGGREGATION = "aggregation"


__all__ = ["EnumBusinessLogicPattern"]
