"""
Timeout Constants.

Centralized constants for timeout values across the ONEX framework.
These constants provide a single source of truth for timeout-related
configuration, replacing hardcoded magic numbers throughout the codebase.

Overview
--------
This module defines timeout constants organized into the following categories:

1. **Standard Timeout Values**: Core operational timeouts (default, long)
2. **Timeout Bounds**: Minimum and maximum allowed timeout values
3. **Thread/Process Timeouts**: Concurrency and shutdown management
4. **Network Timeouts**: HTTP, Kafka, WebSocket communication
5. **Database Timeouts**: Query execution limits
6. **File I/O Timeouts**: Filesystem operations
7. **Cache Timeouts**: TTL for cached data

Value Relationships
-------------------
The timeout values follow a deliberate ordering hierarchy:

**Bounds Hierarchy (milliseconds)**::

    TIMEOUT_MIN_MS (1s) < TIMEOUT_DEFAULT_MS (30s) < TIMEOUT_LONG_MS (5m) < TIMEOUT_MAX_MS (10m)
         1,000                30,000                    300,000                 600,000

**Network Timeout Ordering (seconds)**::

    KAFKA_REQUEST_TIMEOUT (5s) < WEBSOCKET_PING (10s) < HTTP_REQUEST (30s)
            5                          10                      30

    Rationale: Real-time protocols (Kafka, WebSocket) expect faster responses
    than general HTTP requests.

**Process Lifecycle Ordering (seconds)**::

    THREAD_JOIN (5s) < PROCESS_SHUTDOWN (10s)
          5                   10

    Rationale: Threads should complete before process terminates. The process
    shutdown timeout provides a buffer for thread cleanup.

**I/O Type Ordering (seconds)**::

    HTTP_REQUEST (30s) = DATABASE_QUERY (30s) < FILE_IO (60s)
          30                  30                    60

    Rationale: Disk I/O can be slower than network operations, especially on
    network-mounted filesystems or when handling large files.

**Unit Equivalences**::

    TIMEOUT_DEFAULT_MS (30,000ms) == HTTP_REQUEST_TIMEOUT_SECONDS (30s)
    TIMEOUT_DEFAULT_MS (30,000ms) == DATABASE_QUERY_TIMEOUT_SECONDS (30s)
    TIMEOUT_LONG_MS (300,000ms) == DEFAULT_CACHE_TTL_SECONDS (300s)

Usage Guidelines
----------------
1. **Always use bounds validation**: When accepting user-provided timeouts,
   validate against TIMEOUT_MIN_MS and TIMEOUT_MAX_MS.

2. **Match units carefully**: Some constants are in milliseconds (suffix _MS),
   others in seconds (suffix _SECONDS). Always verify the unit before use.

3. **Prefer explicit timeouts**: Use TIMEOUT_DEFAULT_MS only as a fallback.
   Production code should specify appropriate timeouts based on operation type.

4. **Consider operation type**:
   - Fast operations (health checks): Use values near TIMEOUT_MIN_MS
   - Standard I/O (API calls, queries): Use TIMEOUT_DEFAULT_MS
   - Complex workflows (orchestrators): Use TIMEOUT_LONG_MS
   - Never exceed TIMEOUT_MAX_MS

5. **Environment considerations**:
   - Development: Default values are generally appropriate
   - Production: Consider network latency, load, and SLA requirements
   - Testing: May need shorter timeouts for faster feedback

These constants are used by:
- ModelEffectOperation: operation timeout bounds
- ModelSecurityVerification: security verification timeout
- ModelOrchestratorConfig: orchestrator workflow timeout
- ModelHttpIOConfig, ModelDbIOConfig, ModelKafkaIOConfig: I/O timeouts
- constants_effect_limits: Aliases for effect-specific validation
- Any component requiring standardized timeout values

See Also
--------
- constants_effect_limits.py: Effect-specific timeout aliases (EFFECT_TIMEOUT_*)
- constants_field_limits.py: MAX_TIMEOUT_MS for DoS protection (24 hours)

Author: ONEX Framework Team
Version: 1.1.0
"""

# =============================================================================
# Standard Timeout Values (milliseconds)
# =============================================================================
#
# These are the primary timeout constants for general use. Choose based on
# operation complexity:
#   - Simple operations: TIMEOUT_DEFAULT_MS (30s)
#   - Complex/multi-step operations: TIMEOUT_LONG_MS (5m)
#
# Relationship: TIMEOUT_MIN_MS < TIMEOUT_DEFAULT_MS < TIMEOUT_LONG_MS < TIMEOUT_MAX_MS
# =============================================================================

# Default timeout: 30 seconds (30000ms)
#
# Purpose: Standard timeout for typical I/O operations including:
#   - REST API calls to external services
#   - Database queries (simple to moderately complex)
#   - Message queue publish/consume operations
#   - File reads/writes for typical file sizes
#
# Rationale: 30 seconds balances responsiveness with reliability:
#   - Short enough to fail fast on hung connections
#   - Long enough for 95th percentile of normal operations
#   - Matches common HTTP client defaults (requests, httpx)
#
# Relationships:
#   - Equals: HTTP_REQUEST_TIMEOUT_SECONDS, DATABASE_QUERY_TIMEOUT_SECONDS
#   - Aliased by: constants_effect_limits.EFFECT_TIMEOUT_DEFAULT_MS
#   - Aliased by: constants_effect.DEFAULT_OPERATION_TIMEOUT_MS
#
# Units: Milliseconds (divide by 1000 for seconds)
TIMEOUT_DEFAULT_MS: int = 30000

# Long timeout: 5 minutes (300000ms)
#
# Purpose: Extended timeout for complex, multi-step operations including:
#   - Orchestrator workflows coordinating multiple nodes
#   - Security verification with external identity providers
#   - Batch processing and bulk data operations
#   - Complex database migrations or analytical queries
#   - Large file uploads/downloads
#
# Rationale: 5 minutes provides buffer for:
#   - Multi-step workflows with sequential dependencies
#   - Operations that may involve human-in-the-loop delays
#   - Retry attempts within the operation itself
#
# Relationships:
#   - Equals: DEFAULT_CACHE_TTL_SECONDS (same numeric value, different units)
#   - 10x TIMEOUT_DEFAULT_MS
#   - 50% of TIMEOUT_MAX_MS
#
# Warning: Operations approaching this timeout should consider:
#   - Breaking into smaller, independently-timed steps
#   - Using async/background processing patterns
#   - Implementing progress reporting
#
# Units: Milliseconds (divide by 1000 for seconds)
TIMEOUT_LONG_MS: int = 300000

# =============================================================================
# Timeout Bounds (milliseconds)
# =============================================================================
#
# These constants define the valid range for all timeout values in the system.
# Use these for input validation when accepting user-provided timeouts.
#
# Invariant: TIMEOUT_MIN_MS <= user_timeout <= TIMEOUT_MAX_MS
#
# Note: constants_field_limits.MAX_TIMEOUT_MS (24 hours) exists for DoS
# protection in configuration parsing, but operational timeouts should
# never approach that value.
# =============================================================================

# Minimum timeout: 1 second (1000ms)
#
# Purpose: Lower bound for all timeout values in production code.
#
# Rationale: Sub-second timeouts are problematic because:
#   - Network jitter can cause false timeout failures
#   - TCP handshake alone can take 100-300ms across regions
#   - TLS negotiation adds additional overhead
#   - Minor GC pauses or system load can exceed sub-second thresholds
#
# Use cases for minimum timeout:
#   - Health checks (where fast failure is desired)
#   - Cache lookups (expected to be fast)
#   - In-memory operations with I/O fallback
#
# Relationships:
#   - Aliased by: constants_effect_limits.EFFECT_TIMEOUT_MIN_MS
#   - Lower bound for all other timeout constants in this module
#
# Warning: Do not use for actual operations unless fast failure is
# explicitly desired (e.g., circuit breaker probes).
#
# Units: Milliseconds
TIMEOUT_MIN_MS: int = 1000

# Maximum timeout: 10 minutes (600000ms)
#
# Purpose: Upper bound to prevent resource exhaustion from hung operations.
#
# Rationale: 10 minutes is chosen as the upper bound because:
#   - Prevents indefinite connection/thread blocking
#   - Still allows legitimately long operations (batch jobs, migrations)
#   - Beyond this, operations should use async patterns or job queues
#   - Aligns with common load balancer timeout defaults
#
# Operations exceeding this timeout should:
#   - Be redesigned as background/async jobs
#   - Use job queue patterns (Celery, RQ, etc.)
#   - Implement checkpointing and resumability
#   - Report progress to callers
#
# Relationships:
#   - Aliased by: constants_effect_limits.EFFECT_TIMEOUT_MAX_MS
#   - Upper bound for all other timeout constants in this module
#   - 2x TIMEOUT_LONG_MS
#   - See also: constants_field_limits.MAX_TIMEOUT_MS for config parsing
#
# Units: Milliseconds
TIMEOUT_MAX_MS: int = 600000

# =============================================================================
# Thread/Process Timeouts (seconds)
# =============================================================================
#
# Timeouts for concurrency primitives and process lifecycle management.
# These are specified in seconds (float) rather than milliseconds for
# compatibility with Python's threading and multiprocessing APIs.
#
# Ordering Constraint: THREAD_JOIN < PROCESS_SHUTDOWN
# Rationale: Threads must complete before process terminates to ensure
# proper cleanup and avoid orphaned resources.
# =============================================================================

# Thread join timeout: 5 seconds
#
# Purpose: Maximum wait time for thread.join() operations during cleanup.
#
# Rationale: 5 seconds balances:
#   - Sufficient time for I/O operations to complete
#   - Prevention of indefinite blocking during shutdown
#   - Alignment with typical container orchestrator grace periods
#
# Use cases:
#   - Worker thread shutdown in thread pools
#   - Background task cancellation
#   - Cleanup during exception handling
#
# Relationships:
#   - Must be less than PROCESS_SHUTDOWN_TIMEOUT_SECONDS
#   - 50% of PROCESS_SHUTDOWN_TIMEOUT_SECONDS (provides buffer)
#   - 5x TIMEOUT_MIN_MS in seconds
#
# Warning: If threads consistently timeout, investigate for:
#   - Blocking I/O without timeouts
#   - Deadlocks in thread synchronization
#   - Missing cancellation token checks
#
# Units: Seconds (float for API compatibility)
THREAD_JOIN_TIMEOUT_SECONDS: float = 5.0

# Process shutdown timeout: 10 seconds
#
# Purpose: Grace period for process shutdown before forced termination.
#
# Rationale: 10 seconds provides time for:
#   - Thread pool shutdown (via THREAD_JOIN_TIMEOUT_SECONDS)
#   - Buffer flushing (logs, metrics, traces)
#   - Connection pool draining
#   - Cleanup handlers and atexit functions
#
# Use cases:
#   - Subprocess termination in orchestrators
#   - Worker process shutdown in multiprocessing pools
#   - Container/pod termination handling
#
# Relationships:
#   - Must be greater than THREAD_JOIN_TIMEOUT_SECONDS
#   - 2x THREAD_JOIN_TIMEOUT_SECONDS (allows thread cleanup + overhead)
#   - Aligns with Kubernetes default terminationGracePeriodSeconds (30s)
#     but shorter since ONEX apps are designed for fast shutdown
#
# Container Considerations:
#   - Set container terminationGracePeriodSeconds > this value
#   - SIGTERM handler should initiate shutdown within 1-2 seconds
#   - Reserve time for container runtime overhead
#
# Units: Seconds (float for API compatibility)
PROCESS_SHUTDOWN_TIMEOUT_SECONDS: float = 10.0

# =============================================================================
# Network Timeouts (seconds/milliseconds)
# =============================================================================
#
# Timeouts for various network protocols. Note the mixed units:
#   - HTTP and WebSocket use seconds (Python client convention)
#   - Kafka uses milliseconds (Kafka client convention)
#
# Ordering: KAFKA < WEBSOCKET < HTTP
# Rationale: Real-time protocols expect faster responses than request/response
# protocols. Kafka and WebSocket are designed for low-latency streaming.
# =============================================================================

# HTTP request timeout: 30 seconds
#
# Purpose: Default timeout for HTTP/HTTPS client requests.
#
# Rationale: 30 seconds aligns with:
#   - TIMEOUT_DEFAULT_MS (same value, different units)
#   - Python requests library default behavior
#   - Common API gateway timeout defaults
#
# Suitable for:
#   - REST API calls to external services
#   - Webhook deliveries
#   - OAuth token exchanges
#   - File downloads (small to medium)
#
# Relationships:
#   - Equals: TIMEOUT_DEFAULT_MS / 1000
#   - Equals: DATABASE_QUERY_TIMEOUT_SECONDS
#   - Less than: FILE_IO_TIMEOUT_SECONDS (disk can be slower)
#   - Greater than: WEBSOCKET_PING_TIMEOUT_SECONDS (HTTP is request/response)
#
# Note: For large file transfers or slow APIs, use explicit larger timeouts.
#
# Units: Seconds (float for httpx/requests compatibility)
HTTP_REQUEST_TIMEOUT_SECONDS: float = 30.0

# Kafka request timeout: 5000ms (5 seconds)
#
# Purpose: Timeout for individual Kafka broker requests.
#
# Rationale: Kafka is designed for low-latency streaming, so:
#   - 5 seconds is sufficient for most broker operations
#   - Faster failure enables quicker failover to other brokers
#   - Aligns with Kafka's default request.timeout.ms
#
# Applies to:
#   - Producer send operations
#   - Consumer fetch operations
#   - Admin client operations
#   - Metadata refresh requests
#
# Relationships:
#   - Shortest network timeout (real-time protocol)
#   - 5x TIMEOUT_MIN_MS (provides jitter buffer)
#   - Less than: WEBSOCKET_PING_TIMEOUT_SECONDS
#   - Less than: HTTP_REQUEST_TIMEOUT_SECONDS
#
# Kafka-specific considerations:
#   - Total delivery timeout = retries * (request_timeout + backoff)
#   - For producers, also consider delivery.timeout.ms
#   - Consumer poll() has separate max.poll.interval.ms
#
# Units: Milliseconds (Kafka client convention)
KAFKA_REQUEST_TIMEOUT_MS: int = 5000  # env-var-ok: constant definition

# WebSocket ping timeout: 10 seconds
#
# Purpose: Maximum wait time for WebSocket ping/pong health checks.
#
# Rationale: WebSocket connections require active liveness detection:
#   - 10 seconds catches dead connections promptly
#   - Allows for temporary network hiccups without false positives
#   - Short enough to free resources from stale connections
#
# Use cases:
#   - Client connection health monitoring
#   - Server-side connection management
#   - Load balancer health checks
#
# Relationships:
#   - Between KAFKA and HTTP (streaming, but not as latency-critical)
#   - 2x KAFKA_REQUEST_TIMEOUT_MS in seconds
#   - Less than HTTP (WebSocket expects lower latency)
#   - Equals: PROCESS_SHUTDOWN_TIMEOUT_SECONDS (coincidental)
#
# Best Practices:
#   - Send pings at 1/3 to 1/2 of this interval
#   - Implement exponential backoff for reconnection
#   - Consider connection pool limits
#
# Units: Seconds (float for websockets library compatibility)
WEBSOCKET_PING_TIMEOUT_SECONDS: float = 10.0

# =============================================================================
# Database Timeouts (seconds)
# =============================================================================
#
# Timeouts for database operations. These apply to query execution time,
# not connection acquisition (which should be faster, typically 1-5 seconds).
#
# Note: For connection pool acquire timeouts, use a smaller value
# (typically 5-10 seconds) to fail fast when the pool is exhausted.
# =============================================================================

# Database query timeout: 30 seconds
#
# Purpose: Maximum execution time for individual database queries.
#
# Rationale: 30 seconds provides time for:
#   - Simple CRUD operations (typically < 100ms)
#   - Moderate joins and aggregations (1-5 seconds)
#   - Index-assisted analytical queries (5-20 seconds)
#   - Buffer for lock contention and I/O waits
#
# Suitable for:
#   - OLTP workloads (transactional queries)
#   - Simple reporting queries
#   - Most ORM-generated queries
#
# Not suitable for:
#   - Large batch operations (use explicit longer timeout)
#   - Full table scans on large tables
#   - Complex analytical queries (OLAP)
#   - Database migrations (use TIMEOUT_LONG_MS)
#
# Relationships:
#   - Equals: HTTP_REQUEST_TIMEOUT_SECONDS (API calls often include DB queries)
#   - Equals: TIMEOUT_DEFAULT_MS / 1000
#   - Less than: FILE_IO_TIMEOUT_SECONDS
#
# Best Practices:
#   - Set statement_timeout at the database level as backup
#   - Use query EXPLAIN to identify slow queries
#   - Consider connection pool exhaustion if timeouts increase
#   - For PostgreSQL: Also configure idle_in_transaction_session_timeout
#
# Units: Seconds (float as expected by database drivers)
DATABASE_QUERY_TIMEOUT_SECONDS: float = 30.0  # env-var-ok: constant definition

# =============================================================================
# File I/O Timeouts (seconds)
# =============================================================================
#
# Timeouts for filesystem operations. File I/O can be slower than network
# operations due to disk seek times, NFS/network filesystems, and large
# file handling.
#
# Ordering: HTTP/DB (30s) < FILE_IO (60s)
# Rationale: Disk I/O has higher variability than network I/O.
# =============================================================================

# File I/O timeout: 60 seconds
#
# Purpose: Maximum time for file read/write operations.
#
# Rationale: 60 seconds (2x network timeout) accommodates:
#   - Large file operations (multi-MB files)
#   - Network-mounted filesystems (NFS, SMB, cloud storage)
#   - Disk I/O during high system load
#   - Antivirus/security scanning overhead on writes
#
# Suitable for:
#   - Configuration file loading
#   - Log file writes
#   - Temporary file operations
#   - Small to medium data file processing
#
# Not suitable for:
#   - Large file transfers (100+ MB) - use streaming with progress
#   - Video/media processing - use job queues
#   - Batch file processing - use explicit larger timeout
#
# Relationships:
#   - 2x HTTP_REQUEST_TIMEOUT_SECONDS (disk slower than network)
#   - 2x DATABASE_QUERY_TIMEOUT_SECONDS
#   - Less than: TIMEOUT_LONG_MS / 1000 (file ops shouldn't need 5 min)
#
# Environment Considerations:
#   - Local SSD: Rarely approaches this timeout
#   - HDD: May approach timeout for large sequential reads
#   - NFS/Cloud: Highly variable, consider explicit timeouts
#   - Container volumes: Performance depends on driver
#
# Units: Seconds (float as expected by file operation APIs)
FILE_IO_TIMEOUT_SECONDS: float = 60.0

# =============================================================================
# Cache Timeouts (seconds)
# =============================================================================
#
# Time-to-live values for cached data. These control cache expiration,
# not operation timeouts. Longer TTLs improve performance but may serve
# stale data.
#
# Note: Cache TTL is fundamentally different from operation timeouts:
#   - Operation timeouts: "How long to wait for an operation"
#   - Cache TTL: "How long to keep data before considering it stale"
# =============================================================================

# Default cache TTL: 300 seconds (5 minutes)
#
# Purpose: Default time-to-live for cached data before expiration.
#
# Rationale: 5 minutes balances:
#   - Cache hit efficiency (reduces backend load)
#   - Data freshness (changes propagate within 5 minutes)
#   - Memory usage (prevents unbounded growth)
#
# Suitable for:
#   - Configuration lookups (rarely change)
#   - Service discovery results (endpoints stable)
#   - Computed values (expensive to regenerate)
#   - User session data (moderate staleness acceptable)
#
# Not suitable for:
#   - Real-time data (use shorter TTL or no cache)
#   - Frequently updated data (use event-driven invalidation)
#   - Security-critical data (use explicit short TTL)
#
# Relationships:
#   - Equals: TIMEOUT_LONG_MS / 1000 (same numeric value, different semantic)
#   - 10x HTTP_REQUEST_TIMEOUT_SECONDS
#   - Much longer than any operation timeout (caching is for persistence)
#
# Cache Strategies:
#   - For frequently accessed data: Consider longer TTL (15-30 min)
#   - For user-specific data: Consider shorter TTL (1-2 min)
#   - For configuration: Consider event-driven invalidation
#   - For computed values: Consider background refresh
#
# Units: Seconds (int, as TTL doesn't need sub-second precision)
DEFAULT_CACHE_TTL_SECONDS: int = 300

# =============================================================================
# Public API
# =============================================================================
#
# All constants are exported for use by other modules. Organized by category
# to match the module structure above.
#
# Quick Reference (values in parentheses):
#   - TIMEOUT_MIN_MS (1s) < TIMEOUT_DEFAULT_MS (30s) < TIMEOUT_LONG_MS (5m) < TIMEOUT_MAX_MS (10m)
#   - KAFKA (5s) < WEBSOCKET (10s) < HTTP (30s) = DB (30s) < FILE (60s)
#   - THREAD_JOIN (5s) < PROCESS_SHUTDOWN (10s)
# =============================================================================

__all__ = [
    # --- Standard Timeout Values (milliseconds) ---
    # Core timeouts for general use. Most code should use these.
    "TIMEOUT_DEFAULT_MS",  # 30s - Standard I/O operations
    "TIMEOUT_LONG_MS",  # 5m  - Complex workflows, orchestrators
    # --- Timeout Bounds (milliseconds) ---
    # Use for validation of user-provided timeouts.
    "TIMEOUT_MIN_MS",  # 1s  - Minimum allowed timeout
    "TIMEOUT_MAX_MS",  # 10m - Maximum allowed timeout
    # --- Thread/Process Timeouts (seconds) ---
    # Concurrency and lifecycle management.
    "THREAD_JOIN_TIMEOUT_SECONDS",  # 5s  - thread.join() timeout
    "PROCESS_SHUTDOWN_TIMEOUT_SECONDS",  # 10s - Graceful shutdown period
    # --- Network Timeouts (mixed units) ---
    # Protocol-specific timeouts for network operations.
    "HTTP_REQUEST_TIMEOUT_SECONDS",  # 30s - REST API, webhooks
    "KAFKA_REQUEST_TIMEOUT_MS",  # 5s  - Broker request timeout
    "WEBSOCKET_PING_TIMEOUT_SECONDS",  # 10s - Ping/pong health check
    # --- Database Timeouts (seconds) ---
    # Query execution limits.
    "DATABASE_QUERY_TIMEOUT_SECONDS",  # 30s - Query execution
    # --- File I/O Timeouts (seconds) ---
    # Filesystem operation limits.
    "FILE_IO_TIMEOUT_SECONDS",  # 60s - Read/write operations
    # --- Cache Timeouts (seconds) ---
    # TTL for cached data (not operation timeouts).
    "DEFAULT_CACHE_TTL_SECONDS",  # 5m  - Default cache expiration
]
