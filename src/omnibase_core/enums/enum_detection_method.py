from enum import Enum


class EnumDetectionMethod(str, Enum):
    """Methods used for detection."""

    REGEX = "regex"
    ML_MODEL = "ml_model"
    ENTROPY_ANALYSIS = "entropy_analysis"
    DICTIONARY_MATCH = "dictionary_match"
    CONTEXT_ANALYSIS = "context_analysis"
    HYBRID = "hybrid"
