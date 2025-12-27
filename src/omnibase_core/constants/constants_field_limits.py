"""
Centralized field length limits for ONEX models.

This module provides standardized field length limits used across all Pydantic
models in the omnibase_core package. Using these constants ensures consistency
and makes it easy to adjust limits globally.

These constants are used by:
- Model fields requiring max_length validation
- Identifier and name fields across all ONEX models
- Path and URL fields in configuration models
- Content fields such as descriptions, errors, and logs
- Collection fields with size constraints
"""

# =============================================================================
# Identifier Limits
# =============================================================================

# Maximum length for short identifiers (used for IDs, keys, short names)
MAX_IDENTIFIER_LENGTH: int = 100

# Maximum length for display names and titles
MAX_NAME_LENGTH: int = 255

# Maximum length for dictionary/map keys
MAX_KEY_LENGTH: int = 100

# =============================================================================
# Path Limits
# =============================================================================

# Maximum length for file system paths
MAX_PATH_LENGTH: int = 255

# Maximum length for URLs (per RFC 2616 practical limit)
MAX_URL_LENGTH: int = 2048

# =============================================================================
# Content Limits
# =============================================================================

# Maximum length for description fields
MAX_DESCRIPTION_LENGTH: int = 1000

# Maximum length for error messages
MAX_ERROR_MESSAGE_LENGTH: int = 2000

# Maximum length for log messages
MAX_LOG_MESSAGE_LENGTH: int = 4000

# =============================================================================
# Collection Limits
# =============================================================================

# Maximum number of tags per entity
MAX_TAGS_COUNT: int = 50

# Maximum number of labels per entity
MAX_LABELS_COUNT: int = 100

__all__ = [
    # Identifier limits
    "MAX_IDENTIFIER_LENGTH",
    "MAX_NAME_LENGTH",
    "MAX_KEY_LENGTH",
    # Path limits
    "MAX_PATH_LENGTH",
    "MAX_URL_LENGTH",
    # Content limits
    "MAX_DESCRIPTION_LENGTH",
    "MAX_ERROR_MESSAGE_LENGTH",
    "MAX_LOG_MESSAGE_LENGTH",
    # Collection limits
    "MAX_TAGS_COUNT",
    "MAX_LABELS_COUNT",
]
