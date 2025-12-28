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

# =============================================================================
# Thread/Process Timeouts (seconds)
# =============================================================================

# Thread join timeout: 5 seconds
# Rationale: Default timeout for thread.join() operations. Provides sufficient
# time for threads to complete cleanup while preventing indefinite blocking
# during shutdown sequences.
THREAD_JOIN_TIMEOUT_SECONDS: float = 5.0

# Process shutdown timeout: 10 seconds
# Rationale: Timeout for graceful process shutdown. Allows child processes
# adequate time to flush buffers, close connections, and perform cleanup
# before forced termination.
PROCESS_SHUTDOWN_TIMEOUT_SECONDS: float = 10.0

# =============================================================================
# Network Timeouts (seconds/milliseconds)
# =============================================================================

# HTTP request timeout: 30 seconds
# Rationale: Default HTTP request timeout matching TIMEOUT_DEFAULT_MS.
# Suitable for most REST API calls, webhook deliveries, and external
# service integrations.
HTTP_REQUEST_TIMEOUT_SECONDS: float = 30.0

# Kafka request timeout: 5000ms (5 seconds)
# Rationale: Kafka broker request timeout for producer/consumer operations.
# Balances responsiveness with network reliability. Aligns with Kafka's
# default request.timeout.ms configuration.
KAFKA_REQUEST_TIMEOUT_MS: int = 5000

# WebSocket ping timeout: 10 seconds
# Rationale: Timeout for WebSocket ping/pong health checks. A 10-second window
# provides sufficient time for network latency while maintaining responsive
# connection liveness detection. Shorter than HTTP timeout since WebSocket
# connections expect lower latency for real-time communication.
WEBSOCKET_PING_TIMEOUT_SECONDS: float = 10.0

# =============================================================================
# Database Timeouts (seconds)
# =============================================================================

# Database query timeout: 30 seconds
# Rationale: Default timeout for database query operations. Matches the
# standard HTTP request timeout, providing adequate time for typical queries
# including joins and aggregations while preventing runaway queries from
# blocking connections indefinitely.
DATABASE_QUERY_TIMEOUT_SECONDS: float = 30.0

# =============================================================================
# File I/O Timeouts (seconds)
# =============================================================================

# File I/O timeout: 60 seconds
# Rationale: Timeout for file read/write operations. Allows sufficient time
# for larger file operations (multi-MB files, network-mounted filesystems)
# while preventing indefinite hangs on unresponsive storage. Longer than
# network timeouts to accommodate disk I/O variability.
FILE_IO_TIMEOUT_SECONDS: float = 60.0

# =============================================================================
# Cache Timeouts (seconds)
# =============================================================================

# Default cache TTL: 300 seconds (5 minutes)
# Rationale: Default time-to-live for cached data. Provides a balance between
# cache efficiency and data freshness for typical application caches including
# configuration lookups, discovery results, and computed values.
DEFAULT_CACHE_TTL_SECONDS: int = 300

__all__ = [
    # Standard timeout values
    "TIMEOUT_DEFAULT_MS",
    "TIMEOUT_LONG_MS",
    # Timeout bounds
    "TIMEOUT_MIN_MS",
    "TIMEOUT_MAX_MS",
    # Thread/Process timeouts
    "THREAD_JOIN_TIMEOUT_SECONDS",
    "PROCESS_SHUTDOWN_TIMEOUT_SECONDS",
    # Network timeouts
    "HTTP_REQUEST_TIMEOUT_SECONDS",
    "KAFKA_REQUEST_TIMEOUT_MS",
    "WEBSOCKET_PING_TIMEOUT_SECONDS",
    # Database timeouts
    "DATABASE_QUERY_TIMEOUT_SECONDS",
    # File I/O timeouts
    "FILE_IO_TIMEOUT_SECONDS",
    # Cache timeouts
    "DEFAULT_CACHE_TTL_SECONDS",
]
