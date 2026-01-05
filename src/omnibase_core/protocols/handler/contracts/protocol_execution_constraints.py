"""
Protocol for defining execution constraints for a handler.

Domain: Handler contract type definitions for runtime constraints.

This module defines ProtocolExecutionConstraints which specifies resource limits
and operational boundaries for handler execution.

See Also:
    - protocol_handler_behavior_descriptor.py: Determines if retries are safe
    - protocol_handler_contract.py: Aggregates constraints with other specs
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolExecutionConstraints(Protocol):
    """
    Protocol for defining execution constraints for a handler.

    Execution constraints specify resource limits and operational boundaries
    for handler execution. These constraints enable the runtime to enforce
    resource governance, prevent runaway operations, and ensure fair
    resource allocation in multi-tenant environments.

    Execution constraints cover:
        - Retry behavior (max attempts before giving up)
        - Timeout limits (maximum execution duration)
        - Resource limits (memory, CPU allocation)
        - Concurrency limits (parallel execution cap)

    This protocol is useful for:
        - Resource governance and quota enforcement
        - SLA compliance and timeout management
        - Retry policy configuration
        - Container/serverless resource allocation
        - Rate limiting and backpressure

    Attributes:
        max_retries: Maximum retry attempts before failure.
        timeout_seconds: Maximum execution time allowed.
        memory_limit_mb: Optional memory allocation limit.
        cpu_limit: Optional CPU allocation limit.
        concurrency_limit: Optional maximum concurrent executions.

    Example:
        ```python
        class DefaultExecutionConstraints:
            '''Standard execution constraints for production handlers.'''

            @property
            def max_retries(self) -> int:
                return 3  # Try up to 3 times

            @property
            def timeout_seconds(self) -> float:
                return 30.0  # 30 second timeout

            @property
            def memory_limit_mb(self) -> int | None:
                return 512  # 512MB memory limit

            @property
            def cpu_limit(self) -> float | None:
                return 1.0  # One full CPU core

            @property
            def concurrency_limit(self) -> int | None:
                return 10  # Max 10 concurrent executions

        constraints = DefaultExecutionConstraints()
        assert isinstance(constraints, ProtocolExecutionConstraints)

        # Runtime uses constraints for execution governance
        import asyncio

        async with timeout(constraints.timeout_seconds):
            for attempt in range(constraints.max_retries + 1):
                try:
                    result = await handler.execute(input_data)
                    break
                except RetryableError:
                    if attempt == constraints.max_retries:
                        raise MaxRetriesExceededError()
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        ```

    Note:
        Constraints with None values indicate no limit for that resource.
        The runtime should have sensible defaults for None values to
        prevent resource exhaustion.

    See Also:
        ProtocolHandlerBehaviorDescriptor: Determines if retries are safe.
        ProtocolHandlerContract: Aggregates constraints with other specs.
    """

    @property
    def max_retries(self) -> int:
        """
        Maximum number of retry attempts.

        Specifies how many times the runtime should retry a failed handler
        execution before giving up and propagating the error. The total
        number of execution attempts is max_retries + 1 (initial + retries).

        Retry Behavior:
            - 0: No retries, fail immediately on first error
            - 1-3: Standard retry count for transient failures
            - 5+: High retry count for unreliable external services

        Important:
            Only retry if the handler's behavior descriptor indicates
            retry_safe is True. Retrying non-retry-safe handlers may
            cause data corruption or duplicate effects.

        Returns:
            Non-negative integer specifying maximum retry attempts.
            A value of 0 means no retries (single attempt only).
        """
        ...

    @property
    def timeout_seconds(self) -> float:
        """
        Execution timeout in seconds.

        Specifies the maximum duration a single handler execution may run
        before being forcibly terminated. This prevents runaway operations
        and ensures bounded execution time.

        Timeout Considerations:
            - Include network latency for external service calls
            - Account for retry delays if retries are configured
            - Consider downstream timeout chains (avoid timeout < downstream)

        Common Timeout Values:
            - 1-5 seconds: Fast operations, cache lookups
            - 10-30 seconds: Standard API calls, database queries
            - 60-300 seconds: Batch operations, file processing
            - 300+ seconds: Long-running jobs (use async patterns instead)

        Returns:
            Positive float specifying timeout in seconds. Must be > 0.
        """
        ...

    @property
    def memory_limit_mb(self) -> int | None:
        """
        Optional memory limit in megabytes.

        Specifies the maximum memory allocation for handler execution.
        Used for container resource allocation and preventing memory
        exhaustion in shared environments.

        Memory Limit Usage:
            - Container environments: Sets container memory limit
            - Serverless: Configures function memory allocation
            - Process isolation: Enforces memory quota

        Common Memory Limits:
            - 128-256 MB: Simple handlers, stateless operations
            - 512-1024 MB: Standard handlers with moderate data
            - 2048+ MB: Data-intensive handlers, large payloads

        Returns:
            Positive integer specifying memory limit in megabytes,
            or None if no limit should be enforced. A value of None
            means the runtime default applies.
        """
        ...

    @property
    def cpu_limit(self) -> float | None:
        """
        Optional CPU limit as a fraction of cores.

        Specifies the maximum CPU allocation for handler execution.
        Values are expressed as fractions of CPU cores.

        CPU Limit Values:
            - 0.1: 10% of one CPU core
            - 0.5: Half of one CPU core
            - 1.0: One full CPU core
            - 2.0: Two CPU cores
            - None: No limit (use all available)

        Usage Contexts:
            - Kubernetes: Maps to resources.limits.cpu
            - Docker: Maps to --cpus flag
            - Serverless: May affect pricing tier

        Returns:
            Positive float specifying CPU limit as core fraction,
            or None if no limit should be enforced. A value of None
            means the runtime default applies.
        """
        ...

    @property
    def concurrency_limit(self) -> int | None:
        """
        Optional maximum concurrent executions.

        Specifies the maximum number of simultaneous executions of this
        handler. Used for rate limiting, preventing resource exhaustion,
        and protecting downstream services.

        Concurrency Considerations:
            - Database handlers: Limit by connection pool size
            - External API handlers: Limit by rate limit quota
            - CPU-intensive handlers: Limit by available cores
            - Memory-intensive handlers: Limit by available memory

        Common Concurrency Limits:
            - 1: Serialize all executions (mutex behavior)
            - 5-10: Conservative limit for shared resources
            - 50-100: Standard limit for scalable handlers
            - None: No limit (bounded only by system resources)

        Returns:
            Positive integer specifying maximum concurrent executions,
            or None if no limit should be enforced. A value of None
            means unlimited concurrency (bounded only by system capacity).
        """
        ...


__all__ = ["ProtocolExecutionConstraints"]
