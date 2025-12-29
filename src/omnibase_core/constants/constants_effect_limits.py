"""
Effect Subcontract Limits.

Centralized constants for Effect subcontract model validation limits.
Extracting magic numbers improves maintainability and ensures consistency
across all Effect-related models.

These constants are used by:
- ModelEffectOperation: operation_name max length, operation timeout bounds
- ModelEffectSubcontract: subcontract_name max length, max operations
- ModelEffectContractMetadata: author max length
- ModelHttpIOConfig, ModelDbIOConfig, ModelKafkaIOConfig, ModelFilesystemIOConfig: timeout bounds
- ModelResolvedHttpContext, ModelResolvedDbContext, etc.: timeout bounds
"""

from omnibase_core.constants.constants_timeouts import TIMEOUT_DEFAULT_MS

# =============================================================================
# String Length Limits
# =============================================================================

# Maximum length for operation names (used in ModelEffectOperation.operation_name)
EFFECT_OPERATION_NAME_MAX_LENGTH: int = 100

# Maximum length for subcontract names (used in ModelEffectSubcontract.subcontract_name)
EFFECT_SUBCONTRACT_NAME_MAX_LENGTH: int = 100

# Maximum length for author names (used in ModelEffectContractMetadata.author)
EFFECT_AUTHOR_MAX_LENGTH: int = 100

# Maximum length for operation descriptions (used in ModelEffectOperation.description)
EFFECT_OPERATION_DESCRIPTION_MAX_LENGTH: int = 500

# Maximum length for subcontract descriptions (used in ModelEffectSubcontract.description)
EFFECT_SUBCONTRACT_DESCRIPTION_MAX_LENGTH: int = 1000

# =============================================================================
# Collection Limits
# =============================================================================

# Maximum number of operations per subcontract (used in ModelEffectSubcontract.operations)
EFFECT_MAX_OPERATIONS: int = 50

# =============================================================================
# Timeout Bounds (milliseconds)
# =============================================================================

# Minimum timeout: 1 second (1000ms)
# Rationale: Realistic minimum for production I/O operations
EFFECT_TIMEOUT_MIN_MS: int = 1000

# Maximum timeout: 10 minutes (600000ms)
# Rationale: Upper bound to prevent indefinite hangs while allowing long operations
EFFECT_TIMEOUT_MAX_MS: int = 600000

# Default timeout: 30 seconds (30000ms)
# Rationale: Reasonable default for most I/O operations
# Alias to centralized TIMEOUT_DEFAULT_MS (canonical source: constants_timeouts.py).
EFFECT_TIMEOUT_DEFAULT_MS: int = TIMEOUT_DEFAULT_MS

__all__ = [
    # String length limits
    "EFFECT_OPERATION_NAME_MAX_LENGTH",
    "EFFECT_SUBCONTRACT_NAME_MAX_LENGTH",
    "EFFECT_AUTHOR_MAX_LENGTH",
    "EFFECT_OPERATION_DESCRIPTION_MAX_LENGTH",
    "EFFECT_SUBCONTRACT_DESCRIPTION_MAX_LENGTH",
    # Collection limits
    "EFFECT_MAX_OPERATIONS",
    # Timeout bounds
    "EFFECT_TIMEOUT_MIN_MS",
    "EFFECT_TIMEOUT_MAX_MS",
    "EFFECT_TIMEOUT_DEFAULT_MS",
]
