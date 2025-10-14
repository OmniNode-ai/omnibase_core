"""
Health Check Mixin for ONEX Tool Nodes - ONEX Standards Compliant.

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
from collections.abc import Callable as CallableABC
from datetime import UTC, datetime
from typing import Any, Union

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_node_health_status import EnumNodeHealthStatus
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.core.model_health_status import ModelHealthStatus


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
    ) -> list[
        Callable[[], Union[ModelHealthStatus, "asyncio.Future[ModelHealthStatus]"]]
    ]:
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
        base_health = ModelHealthStatus(
            status=EnumNodeHealthStatus.HEALTHY,
            message=f"{self.__class__.__name__} is operational",
            timestamp=datetime.now(UTC).isoformat(),
            uptime_seconds=0,
            memory_usage_mb=0,
            cpu_usage_percent=0.0,
        )

        # Get custom health checks
        health_checks = self.get_health_checks()

        if not health_checks:
            emit_log_event(
                LogLevel.DEBUG,
                "✅ HEALTH_CHECK: No custom checks, returning base health",
                {"status": base_health.status.value},
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
                    result = ModelHealthStatus(
                        status=EnumNodeHealthStatus.UNHEALTHY,
                        message=f"Invalid return type from {check_func.__name__}: {type(result)}",
                        timestamp=datetime.now(UTC).isoformat(),
                        uptime_seconds=0,
                        memory_usage_mb=0,
                        cpu_usage_percent=0.0,
                    )
                check_results.append(result)

                # Update overall status (degraded if any check fails)
                if result.status == EnumNodeHealthStatus.UNHEALTHY:
                    overall_status = EnumNodeHealthStatus.UNHEALTHY
                elif (
                    result.status == EnumNodeHealthStatus.DEGRADED
                    and overall_status != EnumNodeHealthStatus.UNHEALTHY
                ):
                    overall_status = EnumNodeHealthStatus.DEGRADED

                # Collect messages
                if result.message:
                    messages.append(f"{check_func.__name__}: {result.message}")

                emit_log_event(
                    LogLevel.DEBUG,
                    f"✅ Health check completed: {check_func.__name__}",
                    {"check_name": check_func.__name__, "status": result.status.value},
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
                error_result = ModelHealthStatus(
                    status=EnumNodeHealthStatus.UNHEALTHY,
                    message=f"Check failed with error: {e!s}",
                    timestamp=datetime.now(UTC).isoformat(),
                    uptime_seconds=0,
                    memory_usage_mb=0,
                    cpu_usage_percent=0.0,
                )
                check_results.append(error_result)

        # Build final health status
        final_message = base_health.message
        if messages:
            final_message = f"{base_health.message}. Checks: {'; '.join(messages)}"

        final_health = ModelHealthStatus(
            status=overall_status,
            message=final_message,
            timestamp=datetime.now(UTC).isoformat(),
            uptime_seconds=0,
            memory_usage_mb=0,
            cpu_usage_percent=0.0,
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
        base_health = ModelHealthStatus(
            status=EnumNodeHealthStatus.HEALTHY,
            message=f"{self.__class__.__name__} is operational",
            timestamp=datetime.now(UTC).isoformat(),
            uptime_seconds=0,
            memory_usage_mb=0,
            cpu_usage_percent=0.0,
        )

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
                        sync_result = ModelHealthStatus(
                            status=EnumNodeHealthStatus.UNHEALTHY,
                            message=f"Invalid return type from {check_func.__name__}: {type(result)}",
                            timestamp=datetime.now(UTC).isoformat(),
                            uptime_seconds=0,
                            memory_usage_mb=0,
                            cpu_usage_percent=0.0,
                        )

                    async def wrap_sync() -> ModelHealthStatus:
                        return sync_result

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
                check_results.append(result)

                # Update overall status
                if result.status == EnumNodeHealthStatus.UNHEALTHY:
                    overall_status = EnumNodeHealthStatus.UNHEALTHY
                elif (
                    result.status == EnumNodeHealthStatus.DEGRADED
                    and overall_status != EnumNodeHealthStatus.UNHEALTHY
                ):
                    overall_status = EnumNodeHealthStatus.DEGRADED

                if result.message:
                    messages.append(f"{check_name}: {result.message}")

            except Exception as e:
                emit_log_event(
                    LogLevel.ERROR,
                    f"Async health check failed: {check_name}",
                    {"error": str(e)},
                )
                overall_status = EnumNodeHealthStatus.UNHEALTHY
                messages.append(f"{check_name}: ERROR - {e!s}")

        # Build final health status
        final_message = base_health.message
        if messages:
            final_message = f"{base_health.message}. Checks: {'; '.join(messages)}"

        return ModelHealthStatus(
            status=overall_status,
            message=final_message,
            timestamp=datetime.now(UTC).isoformat(),
            uptime_seconds=0,
            memory_usage_mb=0,
            cpu_usage_percent=0.0,
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

            return ModelHealthStatus(
                status=(
                    EnumNodeHealthStatus.HEALTHY
                    if is_healthy
                    else EnumNodeHealthStatus.UNHEALTHY
                ),
                message=f"{dependency_name} is {'available' if is_healthy else 'unavailable'}",
                timestamp=datetime.now(UTC).isoformat(),
                uptime_seconds=0,
                memory_usage_mb=0,
                cpu_usage_percent=0.0,
            )

        except (
            Exception
        ) as e:  # fallback-ok: health check should return UNHEALTHY status, not crash
            return ModelHealthStatus(
                status=EnumNodeHealthStatus.UNHEALTHY,
                message=f"{dependency_name} check failed: {e!s}",
                timestamp=datetime.now(UTC).isoformat(),
                uptime_seconds=0,
                memory_usage_mb=0,
                cpu_usage_percent=0.0,
            )
