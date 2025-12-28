from __future__ import annotations

"""
Health Check Mixin for ONEX Tool Nodes.

Provides standardized health check implementation for tool nodes with comprehensive
error handling, async support, and business intelligence capabilities.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports:
- omnibase_core.errors.error_codes (imports only from types.core_types and enums)
- omnibase_core.enums.enum_log_level (no circular risk)
- omnibase_core.enums.enum_node_health_status (no circular risk)
- omnibase_core.logging.structured (no circular risk)
- omnibase_core.models.core.model_health_status (no circular risk)
- pydantic, typing, datetime (standard library)

Import Chain Position:
1. errors.error_codes → types.core_types
2. THIS MODULE → errors.error_codes (OK - no circle)
3. types.constraints → TYPE_CHECKING import of errors.error_codes
4. models.* → types.constraints

This module can safely import error_codes because error_codes only imports
from types.core_types (not from models or types.constraints).
"""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_node_health_status import EnumNodeHealthStatus
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.health.model_health_status import ModelHealthStatus
from omnibase_core.protocols.http import ProtocolHttpClient
from omnibase_core.types.typed_dict_mixin_types import TypedDictHealthCheckStatus


class MixinHealthCheck:
    """
    Mixin that provides health check capabilities to tool nodes.

    Features:
    - Standard health check endpoint
    - Dependency health aggregation
    - Custom health check hooks
    - Async support

    Usage:
        class MyTool(MixinHealthCheck, ProtocolReducer):
            def get_health_checks(self) -> List[Callable[..., Any]]:
                return [
                    self._check_database,
                    self._check_external_api
                ]

            def _check_database(self) -> ModelHealthStatus:
                # Custom health check logic
                return ModelHealthStatus(
                    status=EnumNodeHealthStatus.HEALTHY,
                    message="Database connection OK"
                )
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the health check mixin."""
        super().__init__(**kwargs)

        emit_log_event(
            LogLevel.DEBUG,
            "🏗️ MIXIN_INIT: Initializing MixinHealthCheck",
            {"mixin_class": self.__class__.__name__},
        )

    def get_health_checks(
        self,
    ) -> list[Callable[[], ModelHealthStatus | asyncio.Future[ModelHealthStatus]]]:
        """
        Get list[Any]of health check functions.

        Override this method to provide custom health checks.
        Each function should return ModelHealthStatus.
        """
        return []

    def health_check(self) -> ModelHealthStatus:
        """
        Perform synchronous health check.

        Returns:
            ModelHealthStatus with aggregated health information
        """
        emit_log_event(
            LogLevel.DEBUG,
            "🏥 HEALTH_CHECK: Starting health check",
            {"node_class": self.__class__.__name__},
        )

        # Basic health - node is running
        base_health = ModelHealthStatus.create_healthy(score=1.0)

        # Get custom health checks
        health_checks = self.get_health_checks()

        if not health_checks:
            emit_log_event(
                LogLevel.DEBUG,
                "✅ HEALTH_CHECK: No custom checks, returning base health",
                {"status": base_health.status},
            )
            return base_health

        # Run all health checks
        check_results: list[ModelHealthStatus] = []
        overall_status = EnumNodeHealthStatus.HEALTHY
        messages: list[str] = []

        for check_func in health_checks:
            try:
                emit_log_event(
                    LogLevel.DEBUG,
                    f"🔍 Running health check: {check_func.__name__}",
                    {"check_name": check_func.__name__},
                )

                result = check_func()

                # Handle async checks in sync context
                if asyncio.iscoroutine(result):
                    emit_log_event(
                        LogLevel.WARNING,
                        f"Async health check called in sync context: {check_func.__name__}",
                        {"check_name": check_func.__name__},
                    )
                    # Run async check synchronously
                    loop = asyncio.new_event_loop()
                    try:
                        async_result = loop.run_until_complete(result)
                        result = async_result
                    finally:
                        loop.close()

                # At this point, result is guaranteed to be ModelHealthStatus
                if not isinstance(result, ModelHealthStatus):
                    emit_log_event(
                        LogLevel.ERROR,
                        f"Health check returned invalid type: {check_func.__name__}",
                        {"check_name": check_func.__name__, "type": str(type(result))},
                    )
                    # Create fallback result for invalid return type
                    from omnibase_core.models.health.model_health_issue import (
                        ModelHealthIssue,
                    )

                    result = ModelHealthStatus.create_unhealthy(
                        score=0.0,
                        issues=[
                            ModelHealthIssue.create_connectivity_issue(
                                message=f"Invalid return type from {check_func.__name__}: {type(result)}",
                                severity="critical",
                            )
                        ],
                    )
                check_results.append(result)

                # Update overall status (degraded if any check fails)
                if result.status == "unhealthy":
                    overall_status = EnumNodeHealthStatus.UNHEALTHY
                elif (
                    result.status == "degraded"
                    and overall_status != EnumNodeHealthStatus.UNHEALTHY
                ):
                    overall_status = EnumNodeHealthStatus.DEGRADED

                # Collect messages - use issues instead
                if result.issues:
                    for issue in result.issues:
                        messages.append(f"{check_func.__name__}: {issue.message}")

                emit_log_event(
                    LogLevel.DEBUG,
                    f"✅ Health check completed: {check_func.__name__}",
                    {"check_name": check_func.__name__, "status": result.status},
                )

            except Exception as e:
                emit_log_event(
                    LogLevel.ERROR,
                    f"❌ Health check failed: {check_func.__name__}",
                    {"check_name": check_func.__name__, "error": str(e)},
                )

                # Mark as unhealthy if check throws
                overall_status = EnumNodeHealthStatus.UNHEALTHY
                messages.append(f"{check_func.__name__}: ERROR - {e!s}")

                # Create error result
                from omnibase_core.models.health.model_health_issue import (
                    ModelHealthIssue,
                )

                error_result = ModelHealthStatus.create_unhealthy(
                    score=0.0,
                    issues=[
                        ModelHealthIssue.create_connectivity_issue(
                            message=f"Check failed with error: {e!s}",
                            severity="critical",
                        )
                    ],
                )
                check_results.append(error_result)

        # Build final health status
        # Calculate health score based on overall status
        health_score = 1.0
        if overall_status == EnumNodeHealthStatus.DEGRADED:
            health_score = 0.6
        elif overall_status == EnumNodeHealthStatus.UNHEALTHY:
            health_score = 0.2

        # Collect all issues from check results
        all_issues = []
        for check_result in check_results:
            all_issues.extend(check_result.issues)

        final_health = ModelHealthStatus(
            status=overall_status.value,
            health_score=health_score,
            issues=all_issues,
        )

        emit_log_event(
            LogLevel.INFO,
            "🏥 HEALTH_CHECK: Health check completed",
            {
                "node_class": self.__class__.__name__,
                "overall_status": overall_status.value,
                "checks_run": len(health_checks),
            },
        )

        return final_health

    async def health_check_async(self) -> ModelHealthStatus:
        """
        Perform asynchronous health check.

        Returns:
            ModelHealthStatus with aggregated health information
        """
        emit_log_event(
            LogLevel.DEBUG,
            "🏥 HEALTH_CHECK_ASYNC: Starting async health check",
            {"node_class": self.__class__.__name__},
        )

        # Basic health - node is running
        base_health = ModelHealthStatus.create_healthy(score=1.0)

        # Get custom health checks
        health_checks = self.get_health_checks()

        if not health_checks:
            return base_health

        # Run all health checks concurrently
        check_tasks = []
        for check_func in health_checks:
            try:
                result = check_func()

                # Convert sync to async if needed
                if not asyncio.iscoroutine(result):
                    # Store the sync result and create a wrapper
                    if isinstance(result, ModelHealthStatus):
                        sync_result = result
                    else:
                        # Handle invalid return type
                        emit_log_event(
                            LogLevel.ERROR,
                            f"Health check {check_func.__name__} returned invalid type: {type(result)}",
                            {
                                "check_name": check_func.__name__,
                                "type": str(type(result)),
                            },
                        )
                        from omnibase_core.models.health.model_health_issue import (
                            ModelHealthIssue,
                        )

                        sync_result = ModelHealthStatus.create_unhealthy(
                            score=0.0,
                            issues=[
                                ModelHealthIssue.create_connectivity_issue(
                                    message=f"Invalid return type from {check_func.__name__}: {type(result)}",
                                    severity="critical",
                                )
                            ],
                        )

                    async def wrap_sync(
                        captured_result: ModelHealthStatus = sync_result,
                    ) -> ModelHealthStatus:
                        return captured_result

                    task = asyncio.create_task(wrap_sync())
                else:
                    task = asyncio.create_task(result)

                check_tasks.append((check_func.__name__, task))

            except Exception as e:
                emit_log_event(
                    LogLevel.ERROR,
                    f"Failed to create health check task: {check_func.__name__}",
                    {"error": str(e)},
                )

        # Wait for all checks to complete
        check_results: list[ModelHealthStatus] = []
        overall_status = EnumNodeHealthStatus.HEALTHY
        messages: list[str] = []

        for check_name, task in check_tasks:
            try:
                result = await task

                # Validate result type (handle invalid return types)
                if not isinstance(result, ModelHealthStatus):
                    emit_log_event(  # type: ignore[unreachable]
                        LogLevel.ERROR,
                        f"Async health check returned invalid type: {check_name}",
                        {"check_name": check_name, "type": str(type(result))},
                    )
                    # Create fallback result for invalid return type
                    from omnibase_core.models.health.model_health_issue import (
                        ModelHealthIssue,
                    )

                    result = ModelHealthStatus.create_unhealthy(
                        score=0.0,
                        issues=[
                            ModelHealthIssue.create_connectivity_issue(
                                message=f"Invalid return type from {check_name}: {type(result)}",
                                severity="critical",
                            )
                        ],
                    )

                check_results.append(result)

                # Update overall status
                if result.status == "unhealthy":
                    overall_status = EnumNodeHealthStatus.UNHEALTHY
                elif (
                    result.status == "degraded"
                    and overall_status != EnumNodeHealthStatus.UNHEALTHY
                ):
                    overall_status = EnumNodeHealthStatus.DEGRADED

                # Collect messages from issues
                if result.issues:
                    for issue in result.issues:
                        messages.append(f"{check_name}: {issue.message}")

            except Exception as e:
                emit_log_event(
                    LogLevel.ERROR,
                    f"Async health check failed: {check_name}",
                    {"error": str(e)},
                )
                overall_status = EnumNodeHealthStatus.UNHEALTHY
                messages.append(f"{check_name}: ERROR - {e!s}")

                # Create error result for failed check
                from omnibase_core.models.health.model_health_issue import (
                    ModelHealthIssue,
                )

                error_result = ModelHealthStatus.create_unhealthy(
                    score=0.0,
                    issues=[
                        ModelHealthIssue.create_connectivity_issue(
                            message=f"Check failed with error: {e!s}",
                            severity="critical",
                        )
                    ],
                )
                check_results.append(error_result)

        # Build final health status
        # Calculate health score based on overall status
        health_score = 1.0
        if overall_status == EnumNodeHealthStatus.DEGRADED:
            health_score = 0.6
        elif overall_status == EnumNodeHealthStatus.UNHEALTHY:
            health_score = 0.2

        # Collect all issues from check results
        all_issues = []
        for check_result in check_results:
            all_issues.extend(check_result.issues)

        return ModelHealthStatus(
            status=overall_status.value,
            health_score=health_score,
            issues=all_issues,
        )

    def get_health_status(self) -> TypedDictHealthCheckStatus:
        """
        Get health status as a typed dictionary.

        Returns a dictionary with basic health information including:
        - node_id: Node identifier
        - is_healthy: Boolean health status
        - status: Health status string
        - health_score: Numeric health score
        - issues: List of issue messages

        Returns:
            TypedDictHealthCheckStatus with health status information
        """
        # Call the proper health_check method
        health = self.health_check()

        # Get node_id safely
        raw_node_id = getattr(self, "node_id", "unknown")
        node_id_str = str(raw_node_id) if raw_node_id else "unknown"

        # Convert to typed dictionary format
        return TypedDictHealthCheckStatus(
            node_id=node_id_str,
            is_healthy=health.status == "healthy",
            status=health.status,
            health_score=health.health_score,
            issues=[issue.message for issue in health.issues],
        )

    def check_dependency_health(
        self,
        dependency_name: str,
        check_func: Callable[[], bool],
    ) -> ModelHealthStatus:
        """
        Helper method to check a dependency's health.

        Args:
            dependency_name: Name of the dependency
            check_func: Function that returns True if healthy

        Returns:
            ModelHealthStatus for the dependency
        """
        try:
            is_healthy = check_func()

            if is_healthy:
                return ModelHealthStatus.create_healthy(score=1.0)
            else:
                from omnibase_core.models.health.model_health_issue import (
                    ModelHealthIssue,
                )

                return ModelHealthStatus.create_unhealthy(
                    score=0.0,
                    issues=[
                        ModelHealthIssue.create_connectivity_issue(
                            message=f"{dependency_name} is unavailable",
                            severity="high",
                        )
                    ],
                )

        except (
            Exception
        ) as e:  # fallback-ok: health check should return UNHEALTHY status, not crash
            from omnibase_core.models.health.model_health_issue import ModelHealthIssue

            return ModelHealthStatus.create_unhealthy(
                score=0.0,
                issues=[
                    ModelHealthIssue.create_connectivity_issue(
                        message=f"{dependency_name} check failed: {e!s}",
                        severity="critical",
                    )
                ],
            )


# Service-specific health check utility functions


async def check_postgresql_health(
    connection_pool: Any,
    timeout_seconds: float = 3.0,
) -> ModelHealthStatus:
    """
    Check PostgreSQL database health.

    Tests database connectivity by executing a simple query.
    Compatible with asyncpg, psycopg3, and SQLAlchemy async engines.

    Args:
        connection_pool: Database connection pool or engine
        timeout_seconds: Timeout for the health check query

    Returns:
        ModelHealthStatus with connectivity details

    Example:
        async def _check_database(self) -> ModelHealthStatus:
            return await check_postgresql_health(
                self.db_pool,
                timeout_seconds=2.0
            )
    """
    from omnibase_core.models.health.model_health_issue import ModelHealthIssue

    try:
        # Try asyncpg-style connection pool
        if hasattr(connection_pool, "execute"):
            # asyncpg pool
            await asyncio.wait_for(
                connection_pool.execute("SELECT 1"),
                timeout=timeout_seconds,
            )
        elif hasattr(connection_pool, "connection"):
            # SQLAlchemy async engine
            async with connection_pool.connection() as conn:
                await asyncio.wait_for(
                    conn.execute("SELECT 1"),
                    timeout=timeout_seconds,
                )
        else:
            # Fallback: assume healthy if pool exists
            emit_log_event(
                LogLevel.WARNING,
                "PostgreSQL health check: Unknown connection pool type",
                {"pool_type": type(connection_pool).__name__},
            )

        return ModelHealthStatus.create_healthy(score=1.0)

    except TimeoutError:
        return ModelHealthStatus.create_unhealthy(
            score=0.0,
            issues=[
                ModelHealthIssue.create_connectivity_issue(
                    message=f"PostgreSQL query timed out after {timeout_seconds}s",
                    severity="critical",
                )
            ],
        )

    except (
        Exception
    ) as e:  # fallback-ok: health check should return UNHEALTHY status, not crash
        emit_log_event(
            LogLevel.ERROR,
            "PostgreSQL health check failed",
            {"error": str(e), "error_type": type(e).__name__},
        )

        return ModelHealthStatus.create_unhealthy(
            score=0.0,
            issues=[
                ModelHealthIssue.create_connectivity_issue(
                    message=f"PostgreSQL connection failed: {e!s}",
                    severity="critical",
                )
            ],
        )


async def check_kafka_health(
    kafka_producer: Any,
    timeout_seconds: float = 3.0,
) -> ModelHealthStatus:
    """
    Check Kafka/Redpanda broker health.

    Tests Kafka connectivity by checking broker connection status.
    Compatible with aiokafka and confluent-kafka async producers.

    Args:
        kafka_producer: Kafka producer instance (aiokafka or confluent-kafka)
        timeout_seconds: Timeout for the health check

    Returns:
        ModelHealthStatus with connectivity details

    Example:
        async def _check_kafka(self) -> ModelHealthStatus:
            return await check_kafka_health(
                self.kafka_producer,
                timeout_seconds=2.0
            )
    """
    from omnibase_core.models.health.model_health_issue import ModelHealthIssue

    try:
        # Check aiokafka-style producer
        if hasattr(kafka_producer, "bootstrap_connected"):
            is_connected = await asyncio.wait_for(
                kafka_producer.bootstrap_connected(),
                timeout=timeout_seconds,
            )

            if not is_connected:
                return ModelHealthStatus.create_unhealthy(
                    score=0.0,
                    issues=[
                        ModelHealthIssue.create_connectivity_issue(
                            message="Kafka broker not connected",
                            severity="critical",
                        )
                    ],
                )

            return ModelHealthStatus.create_healthy(score=1.0)

        # Check confluent-kafka-style producer
        elif hasattr(kafka_producer, "list_topics"):
            # Attempt to list topics (lightweight operation)
            await asyncio.wait_for(
                asyncio.to_thread(kafka_producer.list_topics, timeout=timeout_seconds),
                timeout=timeout_seconds,
            )

            return ModelHealthStatus.create_healthy(score=1.0)

        else:
            # Unknown producer type - assume healthy if exists
            emit_log_event(
                LogLevel.WARNING,
                "Kafka health check: Unknown producer type",
                {"producer_type": type(kafka_producer).__name__},
            )

            return ModelHealthStatus.create_degraded(
                score=0.6,
                issues=[
                    ModelHealthIssue.create_connectivity_issue(
                        message="Kafka producer type not recognized, cannot verify connection",
                        severity="medium",
                    )
                ],
            )

    except TimeoutError:
        return ModelHealthStatus.create_degraded(
            score=0.4,
            issues=[
                ModelHealthIssue.create_connectivity_issue(
                    message=f"Kafka health check timed out after {timeout_seconds}s",
                    severity="high",
                )
            ],
        )

    except (
        Exception
    ) as e:  # fallback-ok: health check should return DEGRADED status, not crash
        emit_log_event(
            LogLevel.ERROR,
            "Kafka health check failed",
            {"error": str(e), "error_type": type(e).__name__},
        )

        return ModelHealthStatus.create_degraded(
            score=0.3,
            issues=[
                ModelHealthIssue.create_connectivity_issue(
                    message=f"Kafka connection check failed: {e!s}",
                    severity="high",
                )
            ],
        )


async def check_redis_health(
    redis_client: Any,
    timeout_seconds: float = 3.0,
) -> ModelHealthStatus:
    """
    Check Redis connection health.

    Tests Redis connectivity by executing a PING command.
    Compatible with aioredis and redis-py async clients.

    Args:
        redis_client: Redis client instance (aioredis or redis-py)
        timeout_seconds: Timeout for the health check

    Returns:
        ModelHealthStatus with connectivity details

    Example:
        async def _check_redis(self) -> ModelHealthStatus:
            return await check_redis_health(
                self.redis_client,
                timeout_seconds=2.0
            )
    """
    from omnibase_core.models.health.model_health_issue import ModelHealthIssue

    try:
        # Execute PING command
        if hasattr(redis_client, "ping"):
            result = await asyncio.wait_for(
                redis_client.ping(),
                timeout=timeout_seconds,
            )

            if result is not True:
                return ModelHealthStatus.create_unhealthy(
                    score=0.0,
                    issues=[
                        ModelHealthIssue.create_connectivity_issue(
                            message=f"Redis PING returned unexpected result: {result}",
                            severity="critical",
                        )
                    ],
                )

            return ModelHealthStatus.create_healthy(score=1.0)

        else:
            emit_log_event(
                LogLevel.WARNING,
                "Redis health check: Unknown client type",
                {"client_type": type(redis_client).__name__},
            )

            return ModelHealthStatus.create_degraded(
                score=0.6,
                issues=[
                    ModelHealthIssue.create_connectivity_issue(
                        message="Redis client type not recognized, cannot verify connection",
                        severity="medium",
                    )
                ],
            )

    except TimeoutError:
        return ModelHealthStatus.create_unhealthy(
            score=0.0,
            issues=[
                ModelHealthIssue.create_connectivity_issue(
                    message=f"Redis PING timed out after {timeout_seconds}s",
                    severity="critical",
                )
            ],
        )

    except (
        Exception
    ) as e:  # fallback-ok: health check should return UNHEALTHY status, not crash
        emit_log_event(
            LogLevel.ERROR,
            "Redis health check failed",
            {"error": str(e), "error_type": type(e).__name__},
        )

        return ModelHealthStatus.create_unhealthy(
            score=0.0,
            issues=[
                ModelHealthIssue.create_connectivity_issue(
                    message=f"Redis connection failed: {e!s}",
                    severity="critical",
                )
            ],
        )


async def check_http_service_health(
    service_url: str,
    timeout_seconds: float = 3.0,
    expected_status: int = 200,
    http_client: ProtocolHttpClient | None = None,
    headers: dict[str, str] | None = None,
    track_duration: bool = False,
) -> ModelHealthStatus:
    """
    Check HTTP service health via health endpoint.

    Makes an HTTP GET request to the service's health endpoint.
    Automatically appends '/health' to the URL if not present.

    Args:
        service_url: Base URL of the service or full health endpoint URL
        timeout_seconds: Request timeout
        expected_status: Expected HTTP status code (default: 200)
        http_client: HTTP client implementing ProtocolHttpClient protocol.
                     If None, returns UNHEALTHY status indicating no client available.
        headers: Optional HTTP headers to include in the request (e.g., for authentication)
        track_duration: If True, capture and include response time in check_duration_ms field
                       (default: False). Useful for detecting service degradation via response
                       time monitoring.

    Returns:
        ModelHealthStatus with connectivity details. If track_duration=True, includes
        response time in the check_duration_ms field (milliseconds).

    Note:
        This function catches all exceptions internally and returns appropriate
        ModelHealthStatus objects. It never raises exceptions to the caller.

    Example:
        async def _check_metadata_service(self) -> ModelHealthStatus:
            # Inject http_client from container or create implementation
            http_client = container.get_service("ProtocolHttpClient")
            return await check_http_service_health(
                "http://metadata-stamping:8057",
                timeout_seconds=2.0,
                http_client=http_client,
                headers={"Authorization": "Bearer token"},
            )

        # With duration tracking for performance monitoring
        async def _check_metadata_service_with_timing(self) -> ModelHealthStatus:
            http_client = container.get_service("ProtocolHttpClient")
            status = await check_http_service_health(
                "http://metadata-stamping:8057",
                timeout_seconds=2.0,
                http_client=http_client,
                track_duration=True,
            )
            # Access duration: status.check_duration_ms
            return status
    """
    from omnibase_core.models.health.model_health_issue import ModelHealthIssue

    # Return unhealthy if no HTTP client is provided
    if http_client is None:
        return ModelHealthStatus.create_unhealthy(
            score=0.0,
            issues=[
                ModelHealthIssue(
                    issue_id=uuid4(),
                    severity="critical",
                    category="configuration",
                    message="No HTTP client provided - inject ProtocolHttpClient implementation",
                    first_detected=datetime.now(UTC),
                    last_seen=datetime.now(UTC),
                )
            ],
        )

    # Validate URL format before making request
    try:
        parsed = urlparse(service_url)
        if not parsed.scheme or not parsed.netloc:
            return ModelHealthStatus.create_unhealthy(
                score=0.0,
                issues=[
                    ModelHealthIssue(
                        issue_id=uuid4(),
                        severity="critical",
                        category="configuration",
                        message=f"Invalid service URL: {service_url}",
                        first_detected=datetime.now(UTC),
                        last_seen=datetime.now(UTC),
                    )
                ],
            )
        if parsed.scheme not in ("http", "https"):
            return ModelHealthStatus.create_unhealthy(
                score=0.0,
                issues=[
                    ModelHealthIssue(
                        issue_id=uuid4(),
                        severity="critical",
                        category="configuration",
                        message=f"Invalid URL scheme '{parsed.scheme}' - must be http or https",
                        first_detected=datetime.now(UTC),
                        last_seen=datetime.now(UTC),
                    )
                ],
            )
    except (
        ValueError,
        AttributeError,
    ) as e:  # urlparse-specific errors: malformed URLs or invalid attribute access
        return ModelHealthStatus.create_unhealthy(
            score=0.0,
            issues=[
                ModelHealthIssue(
                    issue_id=uuid4(),
                    severity="critical",
                    category="configuration",
                    message=f"Failed to parse service URL: {e}",
                    first_detected=datetime.now(UTC),
                    last_seen=datetime.now(UTC),
                )
            ],
        )

    try:
        # Append /health if not already present
        health_url = (
            service_url if service_url.endswith("/health") else f"{service_url}/health"
        )

        # Capture start time if duration tracking is enabled
        start_time = datetime.now(UTC) if track_duration else None

        response = await http_client.get(
            health_url, timeout=timeout_seconds, headers=headers
        )

        # Calculate duration if tracking is enabled
        duration_ms = None
        if track_duration and start_time is not None:
            duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

        if response.status == expected_status:
            return ModelHealthStatus.create_healthy(score=1.0).model_copy(
                update={"check_duration_ms": duration_ms}
                if duration_ms is not None
                else {}
            )
        else:
            return ModelHealthStatus.create_degraded(
                score=0.5,
                issues=[
                    ModelHealthIssue.create_connectivity_issue(
                        message=f"HTTP service returned {response.status}, expected {expected_status}",
                        severity="medium",
                    )
                ],
            ).model_copy(
                update={"check_duration_ms": duration_ms}
                if duration_ms is not None
                else {}
            )

    except TimeoutError:
        return ModelHealthStatus.create_degraded(
            score=0.3,
            issues=[
                ModelHealthIssue.create_connectivity_issue(
                    message=f"HTTP service timed out after {timeout_seconds}s",
                    severity="high",
                )
            ],
        )

    except (
        Exception
    ) as e:  # fallback-ok: health check should return UNHEALTHY status, not crash
        emit_log_event(
            LogLevel.ERROR,
            "HTTP service health check failed",
            {"url": service_url, "error": str(e), "error_type": type(e).__name__},
        )

        return ModelHealthStatus.create_unhealthy(
            score=0.0,
            issues=[
                ModelHealthIssue.create_connectivity_issue(
                    message=f"HTTP health check failed for {service_url}: {type(e).__name__}: {e!s}",
                    severity="critical",
                )
            ],
        )
