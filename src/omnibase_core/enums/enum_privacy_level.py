"""
Privacy level enum for LLM model selection.

Provides strongly-typed privacy levels for model selection and routing
with proper ONEX enum naming conventions.
"""

from enum import Enum


class EnumPrivacyLevel(str, Enum):
    """Privacy levels for LLM model selection."""

    LOCAL_ONLY = "local_only"
    EXTERNAL_OK = "external_ok"
    ANY = "any"
