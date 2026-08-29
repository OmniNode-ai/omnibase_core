# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What a status tile's numeric secondary measures (OMN-16884, Phase C3).

A health board tile is not legible from a severity alone: "DLQ critical" and
"DLQ critical, depth 41,902" are different operational facts. The kind is
declared so a renderer can format the number correctly — a count is an integer,
a rate carries a per-unit interval — without pattern-matching on a label.
"""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper

__all__ = ("EnumStatusSecondaryKind",)


@unique
class EnumStatusSecondaryKind(UtilStrValueHelper, str, Enum):
    """Kind of numeric secondary displayed alongside a tile's status.

    Attributes:
        COUNT: A cardinality — quarantined messages, failing nodes.
        DEPTH: A backlog size — DLQ depth, consumer lag.
        RATE: A per-interval rate — arrivals per minute.
    """

    COUNT = "count"
    DEPTH = "depth"
    RATE = "rate"
