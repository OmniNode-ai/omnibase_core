# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Whether a validation uses a configured backend or a labelled stub."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumModelSwapJudgeMode(UtilStrValueHelper, str, Enum):
    """Whether a validation uses a configured backend or a labelled stub."""

    BACKEND = "backend"
    STUB = "stub"


__all__ = ["EnumModelSwapJudgeMode"]
