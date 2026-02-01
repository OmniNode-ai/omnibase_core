"""
Assembly strategy enum for result assembler tool.

Provides strongly-typed assembly strategies for LLM result combination
with proper ONEX enum naming conventions.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumAssemblyStrategy(StrValueHelper, str, Enum):
    """LLM result assembly strategies."""

    CONCATENATE = "concatenate"
    STRUCTURED_MERGE = "structured_merge"
    WEIGHTED_CONSENSUS = "weighted_consensus"
    BEST_OF_N = "best_of_n"
    COMPARATIVE_ANALYSIS = "comparative_analysis"


__all__ = ["EnumAssemblyStrategy"]
