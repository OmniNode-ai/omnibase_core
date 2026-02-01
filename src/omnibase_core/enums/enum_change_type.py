"""Enum for change proposal types (OMN-1196)."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumChangeType(StrValueHelper, str, Enum):
    """
    Types of system changes that can be proposed.

    Used by ModelChangeProposal to categorize the nature of
    proposed configuration changes.
    """

    MODEL_SWAP = "model_swap"
    """Replace one AI model with another (e.g., GPT-4 -> Claude-3.5)."""

    CONFIG_CHANGE = "config_change"
    """Modify configuration parameters (e.g., temperature: 0.7 -> 0.3)."""

    ENDPOINT_CHANGE = "endpoint_change"
    """Switch provider endpoint URL (e.g., OpenAI -> Azure OpenAI)."""


__all__ = ["EnumChangeType"]
