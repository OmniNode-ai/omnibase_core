# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Handler routing strategy enumeration.

Defines strategies for contract-driven handler routing in ONEX nodes.
Used by MixinHandlerRouting and ModelHandlerRoutingSubcontract.
"""

from enum import Enum

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper

# dispatch-surface-test-ok: OMN-14959 mechanical import-path repoint only (utils/util_str_enum_base -> enums/enum_str_enum_base); no dispatch/routing behavior changed. This file's path matches the handler_routing path heuristic but only its import line was touched, same shape as the other 436 enums files in this PR that don't match the heuristic.


class EnumHandlerRoutingStrategy(UtilStrValueHelper, str, Enum):
    """Handler routing strategy for contract-driven message routing."""

    PAYLOAD_TYPE_MATCH = "payload_type_match"
    """Route by event model class name (orchestrators)."""

    OPERATION_MATCH = "operation_match"
    """Route by operation field value (effects)."""

    TOPIC_PATTERN = "topic_pattern"
    """Route by topic glob pattern (first-match-wins)."""
