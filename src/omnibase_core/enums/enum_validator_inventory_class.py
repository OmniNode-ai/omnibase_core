# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Classification of an omnimarket check (OMN-21503, plan section 0a)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumValidatorInventoryClass(UtilStrValueHelper, str, Enum):
    """VALIDATOR judges an artifact against a rule and moves to omnibase_core.

    DECISION admits an action from runtime facts and stays in omnimarket.
    OTHER is neither (a runner, a reporter, a builder of requests).
    """

    VALIDATOR = "validator"
    DECISION = "decision"
    OTHER = "other"
