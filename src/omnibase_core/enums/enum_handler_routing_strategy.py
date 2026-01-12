# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Handler routing strategy enumeration.

Defines strategies for contract-driven handler routing in ONEX nodes.
Used by MixinHandlerRouting and ModelHandlerRoutingSubcontract.
"""

from enum import Enum


class EnumHandlerRoutingStrategy(str, Enum):
    """Handler routing strategy for contract-driven message routing."""

    PAYLOAD_TYPE_MATCH = "payload_type_match"
    """Route by event model class name (orchestrators)."""

    OPERATION_MATCH = "operation_match"
    """Route by operation field value (effects)."""

    TOPIC_PATTERN = "topic_pattern"
    """Route by topic glob pattern (first-match-wins)."""
