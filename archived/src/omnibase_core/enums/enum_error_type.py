"""
Error type enum for LLM-specific errors.

Provides strongly-typed error types for LLM-specific error handling
with proper ONEX enum naming conventions.
"""

from enum import Enum


class EnumErrorType(str, Enum):
    """LLM-specific error types."""

    HEALTH_CHECK_TIMEOUT = "health_check_timeout"
    SCORING_ERROR = "scoring_error"
    NO_PROVIDERS = "no_providers"
    NO_SUITABLE_PROVIDERS = "no_suitable_providers"
    NO_COMPATIBLE_MODELS = "no_compatible_models"
