# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""How the registry answered one contract load request (OMN-21226)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumContractLoadOutcome(UtilStrValueHelper, str, Enum):
    """How the registry answered one contract load request."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNCHANGED = "unchanged"
    REPLAYED = "replayed"
