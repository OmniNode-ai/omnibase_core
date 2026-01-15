"""Detection methods for sensitive information scanning."""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDetectionMethod(StrValueHelper, str, Enum):
    """Methods used for detection."""

    REGEX = "regex"
    ML_MODEL = "ml_model"
    ENTROPY_ANALYSIS = "entropy_analysis"
    DICTIONARY_MATCH = "dictionary_match"
    CONTEXT_ANALYSIS = "context_analysis"
    HYBRID = "hybrid"


__all__ = ["EnumDetectionMethod"]
