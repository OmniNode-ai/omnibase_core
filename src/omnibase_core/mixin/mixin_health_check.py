"""
Health Check Mixin for ONEX Tool Nodes.

Provides standardized health check implementation for tool nodes.
Supports both synchronous and asynchronous health checks.
"""

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Union

from omnibase.enums.enum_health_status import EnumHealthStatus
from omnibase.enums.enum_log_level import LogLevelEnum

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.model.core.model_health_status import ModelHealthStatus


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
            def get_health_checks(self) -> List[Callable]:
                return [
                    self._check_database,
                    self._check_external_api
                ]

            def _check_database(self) -> ModelHealthStatus:
                # Custom health check logic
                return ModelHealthStatus(
                    status=EnumHealthStatus.HEALTHY,
                    message="Database connection OK"
                )
    """

    def __init__(self, **kwargs):
        """Initialize the health check mixin."""
        super().__init__(**kwargs)

        emit_log_event(
            LogLevelEnum.DEBUG,
            "🏗️ MIXIN_INIT: Initializing MixinHealthCheck",
            {"mixin_class": self.__class__.__name__},
        )

    def get_health_checks(
        self,
    ) -> list[
        Callable[[], Union[ModelHealthStatus, "asyncio.Future[ModelHealthStatus]"]]
    ]:
        """
        Get list of health check functions.

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
            LogLevelEnum.DEBUG,
            "🏥 HEALTH_CHECK: Starting health check",
            {"node_class": self.__class__.__name__},
        )

        # Basic health - node is running
        base_health = ModelHealthStatus(
            status=EnumHealthStatus.HEALTHY,
            message=f"{self.__class__.__name__} is operational",
            timestamp=datetime.utcnow().isoformat(),
        )

        # Get custom health checks
        health_checks = self.get_health_checks()

        if not health_checks:
            emit_log_event(
                LogLevelEnum.DEBUG,
                "✅ HEALTH_CHECK: No custom checks, returning base health",
                {"status": base_health.status.value},
            )
            return base_health

        # Run all health checks
        check_results: list[ModelHealthStatus] = []
        overall_status = EnumHealthStatus.HEALTHY
        messages: list[str] = []

        for check_func in health_checks:
            try:
                emit_log_event(
                    LogLevelEnum.DEBUG,
                    f"🔍 Running health check: {check_func.__name__}",
                    {"check_name": check_func.__name__},
                )

                result = check_func()

                # Handle async checks in sync context
                if asyncio.iscoroutine(result):
                    emit_log_event(
                        LogLevelEnum.WARNING,
                        f"Async health check called in sync context: {check_func.__name__}",
                        {"check_name": check_func.__name__},
                    )
                    # Run async check synchronously
                    loop = asyncio.new_event_loop()
                    try:
                        result = loop.run_until_complete(result)
                    finally:
                        loop.close()

                check_results.append(result)

                # Update overall status (degraded if any check fails)
                if result.status == EnumHealthStatus.UNHEALTHY:
                    overall_status = EnumHealthStatus.UNHEALTHY
                elif (
                    result.status == EnumHealthStatus.DEGRADED
                    and overall_status != EnumHealthStatus.UNHEALTHY
                ):
                    overall_status = EnumHealthStatus.DEGRADED

                # Collect messages
                if result.message:
                    messages.append(f"{check_func.__name__}: {result.message}")

                emit_log_event(
                    LogLevelEnum.DEBUG,
                    f"✅ Health check completed: {check_func.__name__}",
                    {"check_name": check_func.__name__, "status": result.status.value},
                )

            except Exception as e:
                emit_log_event(
                    LogLevelEnum.ERROR,
                    f"❌ Health check failed: {check_func.__name__}",
                    {"check_name": check_func.__name__, "error": str(e)},
                )

                # Mark as unhealthy if check throws
                overall_status = EnumHealthStatus.UNHEALTHY
                messages.append(f"{check_func.__name__}: ERROR - {e!s}")

                # Create error result
                error_result = ModelHealthStatus(
                    status=EnumHealthStatus.UNHEALTHY,
                    message=f"Check failed with error: {e!s}",
                    timestamp=datetime.utcnow().isoformat(),
                )
                check_results.append(error_result)

        # Build final health status
        final_message = base_health.message
        if messages:
            final_message = f"{base_health.message}. Checks: {'; '.join(messages)}"

        final_health = ModelHealthStatus(
            status=overall_status,
            message=final_message,
            timestamp=datetime.utcnow().isoformat(),
        )

        emit_log_event(
            LogLevelEnum.INFO,
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
            LogLevelEnum.DEBUG,
            "🏥 HEALTH_CHECK_ASYNC: Starting async health check",
            {"node_class": self.__class__.__name__},
        )

        # Basic health - node is running
        base_health = ModelHealthStatus(
            status=EnumHealthStatus.HEALTHY,
            message=f"{self.__class__.__name__} is operational",
            timestamp=datetime.utcnow().isoformat(),
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

                    async def wrap_sync():
                        return result

                    task = asyncio.create_task(wrap_sync())
                else:
                    task = asyncio.create_task(result)

                check_tasks.append((check_func.__name__, task))

            except Exception as e:
                emit_log_event(
                    LogLevelEnum.ERROR,
                    f"Failed to create health check task: {check_func.__name__}",
                    {"error": str(e)},
                )

        # Wait for all checks to complete
        check_results: list[ModelHealthStatus] = []
        overall_status = EnumHealthStatus.HEALTHY
        messages: list[str] = []

        for check_name, task in check_tasks:
            try:
                result = await task
                check_results.append(result)

                # Update overall status
                if result.status == EnumHealthStatus.UNHEALTHY:
                    overall_status = EnumHealthStatus.UNHEALTHY
                elif (
                    result.status == EnumHealthStatus.DEGRADED
                    and overall_status != EnumHealthStatus.UNHEALTHY
                ):
                    overall_status = EnumHealthStatus.DEGRADED

                if result.message:
                    messages.append(f"{check_name}: {result.message}")

            except Exception as e:
                emit_log_event(
                    LogLevelEnum.ERROR,
                    f"Async health check failed: {check_name}",
                    {"error": str(e)},
                )
                overall_status = EnumHealthStatus.UNHEALTHY
                messages.append(f"{check_name}: ERROR - {e!s}")

        # Build final health status
        final_message = base_health.message
        if messages:
            final_message = f"{base_health.message}. Checks: {'; '.join(messages)}"

        return ModelHealthStatus(
            status=overall_status,
            message=final_message,
            timestamp=datetime.utcnow().isoformat(),
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
                    EnumHealthStatus.HEALTHY
                    if is_healthy
                    else EnumHealthStatus.UNHEALTHY
                ),
                message=f"{dependency_name} is {'available' if is_healthy else 'unavailable'}",
                timestamp=datetime.utcnow().isoformat(),
            )

        except Exception as e:
            return ModelHealthStatus(
                status=EnumHealthStatus.UNHEALTHY,
                message=f"{dependency_name} check failed: {e!s}",
                timestamp=datetime.utcnow().isoformat(),
            )
