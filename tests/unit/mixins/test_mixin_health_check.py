"""
Test suite for MixinHealthCheck.

Tests health check capabilities, dependency checking, and async support.
"""

import asyncio
from unittest.mock import Mock, patch

import pytest

from omnibase_core.enums.enum_node_health_status import EnumNodeHealthStatus
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.mixins.mixin_health_check import MixinHealthCheck
from omnibase_core.models.core.model_health_status import ModelHealthStatus


class TestNode(MixinHealthCheck):
    """Test node class that uses MixinHealthCheck."""

    def __init__(self):
        super().__init__()
        self.custom_checks = []

    def get_health_checks(self):
        """Return custom health check functions."""
        return self.custom_checks


class TestMixinHealthCheck:
    """Test MixinHealthCheck functionality."""

    def test_initialization(self):
        """Test mixin initialization."""
        node = TestNode()

        assert hasattr(node, "health_check")
        assert hasattr(node, "health_check_async")
        assert hasattr(node, "get_health_checks")
        assert hasattr(node, "check_dependency_health")

    def test_health_check_basic(self):
        """Test basic health check with no custom checks."""
        node = TestNode()

        result = node.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumNodeHealthStatus.HEALTHY
        assert "TestNode" in result.message
        assert "operational" in result.message

    def test_health_check_with_custom_check_healthy(self):
        """Test health check with custom check returning healthy."""

        def custom_check():
            return ModelHealthStatus(
                status=EnumNodeHealthStatus.HEALTHY,
                message="Custom check passed",
                timestamp="2024-01-01T00:00:00Z",
                uptime_seconds=0,
                memory_usage_mb=0,
                cpu_usage_percent=0.0,
            )

        node = TestNode()
        node.custom_checks = [custom_check]

        result = node.health_check()

        assert result.status == EnumNodeHealthStatus.HEALTHY
        assert "Custom check passed" in result.message

    def test_health_check_with_custom_check_unhealthy(self):
        """Test health check with custom check returning unhealthy."""

        def custom_check():
            return ModelHealthStatus(
                status=EnumNodeHealthStatus.UNHEALTHY,
                message="Custom check failed",
                timestamp="2024-01-01T00:00:00Z",
                uptime_seconds=0,
                memory_usage_mb=0,
                cpu_usage_percent=0.0,
            )

        node = TestNode()
        node.custom_checks = [custom_check]

        result = node.health_check()

        assert result.status == EnumNodeHealthStatus.UNHEALTHY
        assert "Custom check failed" in result.message

    def test_health_check_with_custom_check_degraded(self):
        """Test health check with custom check returning degraded."""

        def custom_check():
            return ModelHealthStatus(
                status=EnumNodeHealthStatus.DEGRADED,
                message="Custom check degraded",
                timestamp="2024-01-01T00:00:00Z",
                uptime_seconds=0,
                memory_usage_mb=0,
                cpu_usage_percent=0.0,
            )

        node = TestNode()
        node.custom_checks = [custom_check]

        result = node.health_check()

        assert result.status == EnumNodeHealthStatus.DEGRADED
        assert "Custom check degraded" in result.message

    def test_health_check_with_multiple_checks_all_healthy(self):
        """Test health check with multiple checks, all healthy."""

        def check1():
            return ModelHealthStatus(
                status=EnumNodeHealthStatus.HEALTHY,
                message="Check 1 passed",
                timestamp="2024-01-01T00:00:00Z",
                uptime_seconds=0,
                memory_usage_mb=0,
                cpu_usage_percent=0.0,
            )

        def check2():
            return ModelHealthStatus(
                status=EnumNodeHealthStatus.HEALTHY,
                message="Check 2 passed",
                timestamp="2024-01-01T00:00:00Z",
                uptime_seconds=0,
                memory_usage_mb=0,
                cpu_usage_percent=0.0,
            )

        node = TestNode()
        node.custom_checks = [check1, check2]

        result = node.health_check()

        assert result.status == EnumNodeHealthStatus.HEALTHY
        assert "Check 1 passed" in result.message
        assert "Check 2 passed" in result.message

    def test_health_check_with_multiple_checks_one_fails(self):
        """Test health check with multiple checks, one fails."""

        def check1():
            return ModelHealthStatus(
                status=EnumNodeHealthStatus.HEALTHY,
                message="Check 1 passed",
                timestamp="2024-01-01T00:00:00Z",
                uptime_seconds=0,
                memory_usage_mb=0,
                cpu_usage_percent=0.0,
            )

        def check2():
            return ModelHealthStatus(
                status=EnumNodeHealthStatus.UNHEALTHY,
                message="Check 2 failed",
                timestamp="2024-01-01T00:00:00Z",
                uptime_seconds=0,
                memory_usage_mb=0,
                cpu_usage_percent=0.0,
            )

        node = TestNode()
        node.custom_checks = [check1, check2]

        result = node.health_check()

        assert result.status == EnumNodeHealthStatus.UNHEALTHY

    def test_health_check_with_exception_in_check(self):
        """Test health check when custom check raises exception."""

        def failing_check():
            raise RuntimeError("Check failed with exception")

        node = TestNode()
        node.custom_checks = [failing_check]

        result = node.health_check()

        assert result.status == EnumNodeHealthStatus.UNHEALTHY
        assert "ERROR" in result.message

    def test_health_check_priority_unhealthy_over_degraded(self):
        """Test that UNHEALTHY status takes priority over DEGRADED."""

        def check1():
            return ModelHealthStatus(
                status=EnumNodeHealthStatus.DEGRADED,
                message="Check 1 degraded",
                timestamp="2024-01-01T00:00:00Z",
                uptime_seconds=0,
                memory_usage_mb=0,
                cpu_usage_percent=0.0,
            )

        def check2():
            return ModelHealthStatus(
                status=EnumNodeHealthStatus.UNHEALTHY,
                message="Check 2 unhealthy",
                timestamp="2024-01-01T00:00:00Z",
                uptime_seconds=0,
                memory_usage_mb=0,
                cpu_usage_percent=0.0,
            )

        node = TestNode()
        node.custom_checks = [check1, check2]

        result = node.health_check()

        assert result.status == EnumNodeHealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_health_check_async_basic(self):
        """Test async health check with no custom checks."""
        node = TestNode()

        result = await node.health_check_async()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumNodeHealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_async_with_sync_check(self):
        """Test async health check with synchronous custom check."""

        def sync_check():
            return ModelHealthStatus(
                status=EnumNodeHealthStatus.HEALTHY,
                message="Sync check passed",
                timestamp="2024-01-01T00:00:00Z",
                uptime_seconds=0,
                memory_usage_mb=0,
                cpu_usage_percent=0.0,
            )

        node = TestNode()
        node.custom_checks = [sync_check]

        result = await node.health_check_async()

        assert result.status == EnumNodeHealthStatus.HEALTHY
        assert "Sync check passed" in result.message

    @pytest.mark.asyncio
    async def test_health_check_async_with_async_check(self):
        """Test async health check with asynchronous custom check."""

        async def async_check():
            await asyncio.sleep(0.01)  # Simulate async work
            return ModelHealthStatus(
                status=EnumNodeHealthStatus.HEALTHY,
                message="Async check passed",
                timestamp="2024-01-01T00:00:00Z",
                uptime_seconds=0,
                memory_usage_mb=0,
                cpu_usage_percent=0.0,
            )

        node = TestNode()
        node.custom_checks = [async_check]

        result = await node.health_check_async()

        assert result.status == EnumNodeHealthStatus.HEALTHY
        assert "Async check passed" in result.message

    @pytest.mark.asyncio
    async def test_health_check_async_with_mixed_checks(self):
        """Test async health check with both sync and async checks."""

        def sync_check():
            return ModelHealthStatus(
                status=EnumNodeHealthStatus.HEALTHY,
                message="Sync check passed",
                timestamp="2024-01-01T00:00:00Z",
                uptime_seconds=0,
                memory_usage_mb=0,
                cpu_usage_percent=0.0,
            )

        async def async_check():
            await asyncio.sleep(0.01)
            return ModelHealthStatus(
                status=EnumNodeHealthStatus.HEALTHY,
                message="Async check passed",
                timestamp="2024-01-01T00:00:00Z",
                uptime_seconds=0,
                memory_usage_mb=0,
                cpu_usage_percent=0.0,
            )

        node = TestNode()
        node.custom_checks = [sync_check, async_check]

        result = await node.health_check_async()

        assert result.status == EnumNodeHealthStatus.HEALTHY
        assert "Sync check passed" in result.message
        assert "Async check passed" in result.message

    @pytest.mark.asyncio
    async def test_health_check_async_with_exception(self):
        """Test async health check when check raises exception."""

        async def failing_check():
            raise RuntimeError("Async check failed")

        node = TestNode()
        node.custom_checks = [failing_check]

        result = await node.health_check_async()

        assert result.status == EnumNodeHealthStatus.UNHEALTHY

    def test_check_dependency_health_available(self):
        """Test check_dependency_health with available dependency."""
        node = TestNode()

        def check_func():
            return True

        result = node.check_dependency_health("test_dependency", check_func)

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumNodeHealthStatus.HEALTHY
        assert "test_dependency" in result.message
        assert "available" in result.message

    def test_check_dependency_health_unavailable(self):
        """Test check_dependency_health with unavailable dependency."""
        node = TestNode()

        def check_func():
            return False

        result = node.check_dependency_health("test_dependency", check_func)

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumNodeHealthStatus.UNHEALTHY
        assert "test_dependency" in result.message
        assert "unavailable" in result.message

    def test_check_dependency_health_with_exception(self):
        """Test check_dependency_health when check function raises exception."""
        node = TestNode()

        def check_func():
            raise ConnectionError("Cannot connect to dependency")

        result = node.check_dependency_health("test_dependency", check_func)

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumNodeHealthStatus.UNHEALTHY
        assert "test_dependency" in result.message
        assert "failed" in result.message.lower()

    def test_health_check_with_invalid_return_type(self):
        """Test health check when custom check returns invalid type."""

        def invalid_check():
            return "not a health status object"

        node = TestNode()
        node.custom_checks = [invalid_check]

        result = node.health_check()

        # Should handle gracefully and return unhealthy
        assert result.status == EnumNodeHealthStatus.UNHEALTHY

    def test_health_check_with_async_check_in_sync_context(self):
        """Test health check when async check is called in sync context."""

        async def async_check():
            return ModelHealthStatus(
                status=EnumNodeHealthStatus.HEALTHY,
                message="Async check in sync context",
                timestamp="2024-01-01T00:00:00Z",
                uptime_seconds=0,
                memory_usage_mb=0,
                cpu_usage_percent=0.0,
            )

        node = TestNode()
        node.custom_checks = [async_check]

        # Should handle async check in sync context
        result = node.health_check()

        assert isinstance(result, ModelHealthStatus)

    def test_health_check_multiple_failures(self):
        """Test health check with multiple failing checks."""

        def check1():
            raise ValueError("Check 1 failed")

        def check2():
            raise RuntimeError("Check 2 failed")

        def check3():
            return ModelHealthStatus(
                status=EnumNodeHealthStatus.UNHEALTHY,
                message="Check 3 unhealthy",
                timestamp="2024-01-01T00:00:00Z",
                uptime_seconds=0,
                memory_usage_mb=0,
                cpu_usage_percent=0.0,
            )

        node = TestNode()
        node.custom_checks = [check1, check2, check3]

        result = node.health_check()

        assert result.status == EnumNodeHealthStatus.UNHEALTHY
        assert "ERROR" in result.message or "unhealthy" in result.message.lower()

    def test_get_health_checks_default(self):
        """Test get_health_checks default implementation."""
        mixin = MixinHealthCheck()

        checks = mixin.get_health_checks()

        assert isinstance(checks, list)
        assert len(checks) == 0

    @pytest.mark.asyncio
    async def test_health_check_async_invalid_return_type(self):
        """Test async health check with invalid return type."""

        async def invalid_check():
            return "not a health status"

        node = TestNode()
        node.custom_checks = [invalid_check]

        result = await node.health_check_async()

        assert result.status == EnumNodeHealthStatus.UNHEALTHY

    def test_check_dependency_health_with_none_check_result(self):
        """Test check_dependency_health when check returns None."""
        node = TestNode()

        def check_func():
            return None

        result = node.check_dependency_health("test_dependency", check_func)

        # Should treat None as falsy/unhealthy
        assert result.status == EnumNodeHealthStatus.UNHEALTHY

    def test_check_dependency_health_with_truthy_values(self):
        """Test check_dependency_health with various truthy values."""
        node = TestNode()

        test_cases = [
            (True, EnumNodeHealthStatus.HEALTHY),
            (1, EnumNodeHealthStatus.HEALTHY),
            ("yes", EnumNodeHealthStatus.HEALTHY),
            ([1, 2], EnumNodeHealthStatus.HEALTHY),
        ]

        for value, expected_status in test_cases:

            def check_func():
                return value

            result = node.check_dependency_health("test_dependency", check_func)
            assert result.status == expected_status

    def test_check_dependency_health_with_falsy_values(self):
        """Test check_dependency_health with various falsy values."""
        node = TestNode()

        test_cases = [False, 0, "", [], None]

        for value in test_cases:

            def check_func():
                return value

            result = node.check_dependency_health("test_dependency", check_func)
            assert result.status == EnumNodeHealthStatus.UNHEALTHY
