"""
Handler routing strategy enumeration.

Defines strategies for contract-driven handler routing in ONEX nodes.
Used by MixinHandlerRouting and ModelHandlerRoutingSubcontract.
"""

from enum import Enum

from omnibase_core.utils.util_str_enum_base import StrValueHelper


class EnumHandlerRoutingStrategy(StrValueHelper, str, Enum):
    """Handler routing strategy for contract-driven message routing."""

    PAYLOAD_TYPE_MATCH = "payload_type_match"
    """Route by event model class name (orchestrators)."""

    OPERATION_MATCH = "operation_match"
    """Route by operation field value (effects)."""

    TOPIC_PATTERN = "topic_pattern"
    """Route by topic glob pattern (first-match-wins)."""
