# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Whether a runtime applied one registry change (OMN-21226)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumContractHotloadAppliedStatus(UtilStrValueHelper, str, Enum):
    """Whether a runtime applied one registry change."""

    APPLIED = "applied"
    REFUSED = "refused"
    FAILED = "failed"
