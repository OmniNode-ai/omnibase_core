# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What a prune did with one candidate topic (OMN-21226)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumPruneTopicStatus(UtilStrValueHelper, str, Enum):
    """What a prune did with one candidate topic."""

    RETIRED = "retired"
    SKIPPED = "skipped"
    FAILED = "failed"
