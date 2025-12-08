"""
Constants for effect execution.

Single source of truth for effect-related constants to avoid magic numbers
and ensure consistent defaults across the codebase.

VERSION: 1.0.0

Author: ONEX Framework Team
"""

# ==============================================================================
# Timeout Constants
# ==============================================================================

# Default operation timeout in milliseconds (30 seconds).
# Used as the final fallback when no timeout is specified in:
#   - ModelEffectInput.operation_timeout_ms
#   - ModelEffectOperation.operation_timeout_ms
#   - Individual IO config timeout_ms
#
# This matches the resolved context timeout defaults for consistency.
# For production use, always set explicit timeouts in operation definitions.
DEFAULT_OPERATION_TIMEOUT_MS: int = 30000

# ==============================================================================
# Field Extraction Constants
# ==============================================================================

# Maximum depth for nested field extraction to prevent denial-of-service
# attacks via deeply nested or maliciously crafted field paths.
# Default of 10 is sufficient for typical use cases while preventing abuse.
DEFAULT_MAX_FIELD_EXTRACTION_DEPTH: int = 10

# ==============================================================================
# Retry Constants
# ==============================================================================

# Default maximum retry attempts for idempotent operations.
# Can be overridden in ModelEffectRetryConfig.max_attempts.
DEFAULT_MAX_RETRY_ATTEMPTS: int = 3

# Default base delay between retries in milliseconds.
# Exponential backoff is applied: delay = base_delay * 2^attempt
DEFAULT_RETRY_BASE_DELAY_MS: int = 1000

# Jitter factor for retry delays (0.1 = 10% jitter).
# Jitter prevents retry storms when multiple clients retry simultaneously.
DEFAULT_RETRY_JITTER_FACTOR: float = 0.1

# ==============================================================================
# Circuit Breaker Constants
# ==============================================================================

# Default number of consecutive failures before opening circuit.
DEFAULT_CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5

# Default number of consecutive successes in HALF_OPEN to close circuit.
DEFAULT_CIRCUIT_BREAKER_SUCCESS_THRESHOLD: int = 2

# Default time to wait in OPEN state before entering HALF_OPEN (60 seconds).
DEFAULT_CIRCUIT_BREAKER_TIMEOUT_MS: int = 60000

# ==============================================================================
# Version Validation Constants
# ==============================================================================

# Supported major versions of the effect subcontract schema.
# Used for validating contract compatibility at load time.
SUPPORTED_EFFECT_SUBCONTRACT_MAJOR_VERSIONS: frozenset[int] = frozenset({1})

# Minimum minor version required for the current major version.
# Contracts with lower minor versions may be missing required features.
MIN_EFFECT_SUBCONTRACT_MINOR_VERSION: int = 0
