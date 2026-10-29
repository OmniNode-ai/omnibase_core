# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Evidence verdicts; these never authorize routing changes."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumModelSwapDecision(UtilStrValueHelper, str, Enum):
    """Evidence verdicts; these never authorize routing changes."""

    RECOMMEND = "recommend"
    REJECT = "reject"
    ABSTAIN = "abstain"
    INCONCLUSIVE = "inconclusive"


__all__ = ["EnumModelSwapDecision"]
