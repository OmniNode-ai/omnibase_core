# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Provenance Lane Enum.

Which runtime lane an emitter runs in; UNKNOWN is what a reader reports for an
 event that carries no provenance, never DEV.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumProvenanceLane(UtilStrValueHelper, str, Enum):
    """Runtime lane an emitter runs in.

    UNKNOWN is what a reader reports for an event that carries no provenance,
    never DEV.
    """

    DEV = "dev"
    STABILITY = "stability"
    OTHER = "other"
    UNKNOWN = "unknown"


__all__: list[str] = ["EnumProvenanceLane"]
