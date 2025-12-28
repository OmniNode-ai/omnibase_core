"""
Timeout Constants.

Centralized constants for timeout values across the ONEX framework.
These constants provide a single source of truth for timeout-related
configuration, replacing hardcoded magic numbers throughout the codebase.

These constants are used by:
- ModelEffectOperation: operation timeout bounds
- ModelSecurityVerification: security verification timeout
- ModelOrchestratorConfig: orchestrator workflow timeout
- ModelHttpIOConfig, ModelDbIOConfig, ModelKafkaIOConfig: I/O timeouts
- Any component requiring standardized timeout values

VERSION: 1.0.0

Author: ONEX Framework Team
"""

# =============================================================================
# Standard Timeout Values (milliseconds)
# =============================================================================

# Default timeout: 30 seconds (30000ms)
# Rationale: Reasonable default for most I/O operations. Balances responsiveness
# with allowing sufficient time for typical network requests, database queries,
# and other standard operations.
TIMEOUT_DEFAULT_MS: int = 30000

# Long timeout: 5 minutes (300000ms)
# Rationale: Used for operations that legitimately require extended time:
#   - Orchestrator workflows coordinating multiple nodes
#   - Security verification operations requiring external validation
#   - Batch processing operations
#   - Complex database migrations or queries
TIMEOUT_LONG_MS: int = 300000

# =============================================================================
# Timeout Bounds (milliseconds)
# =============================================================================

# Minimum timeout: 1 second (1000ms)
# Rationale: Realistic minimum for production I/O operations. Setting timeouts
# below this value risks false negatives due to network jitter or minor delays.
# Even the fastest operations should allow at least 1 second to complete.
TIMEOUT_MIN_MS: int = 1000

# Maximum timeout: 10 minutes (600000ms)
# Rationale: Upper bound to prevent indefinite hangs while allowing legitimately
# long operations. Operations exceeding 10 minutes should be redesigned as
# asynchronous workflows or broken into smaller chunks.
TIMEOUT_MAX_MS: int = 600000

__all__ = [
    # Standard timeout values
    "TIMEOUT_DEFAULT_MS",
    "TIMEOUT_LONG_MS",
    # Timeout bounds
    "TIMEOUT_MIN_MS",
    "TIMEOUT_MAX_MS",
]
