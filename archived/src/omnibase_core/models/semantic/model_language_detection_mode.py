"""
Language detection mode enumeration.

Defines the available modes for language detection and processing
during text preprocessing operations in the semantic discovery engine.
"""

from enum import Enum


class ModelLanguageDetectionMode(str, Enum):
    """Language detection and processing mode."""

    AUTO_DETECT = "auto_detect"
    FORCED = "forced"
    MULTI_LANGUAGE = "multi_language"
    DISABLED = "disabled"
