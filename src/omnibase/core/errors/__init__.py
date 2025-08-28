"""
ONEX Core Error Classes

Centralized error handling for the ONEX system.
"""

from omnibase.core.core_errors import CoreErrorCode, OnexError
from omnibase.core.errors.document_freshness_errors import (
    DocumentFreshnessAIServiceError,
    DocumentFreshnessAnalysisError,
    DocumentFreshnessChangeDetectionError,
    DocumentFreshnessDatabaseError,
    DocumentFreshnessDependencyError,
    DocumentFreshnessError,
    DocumentFreshnessPathError,
    DocumentFreshnessSystemError,
    DocumentFreshnessValidationError,
)

__all__ = [
    "CoreErrorCode",
    "OnexError",
    "DocumentFreshnessError",
    "DocumentFreshnessPathError",
    "DocumentFreshnessDatabaseError",
    "DocumentFreshnessAnalysisError",
    "DocumentFreshnessAIServiceError",
    "DocumentFreshnessDependencyError",
    "DocumentFreshnessChangeDetectionError",
    "DocumentFreshnessValidationError",
    "DocumentFreshnessSystemError",
]
