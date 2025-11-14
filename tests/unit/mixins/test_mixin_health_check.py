"""
Test suite for MixinHealthCheck.

Tests health check capabilities, dependency checking, and async support.
"""

import asyncio
from unittest.mock import Mock, patch

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_node_health_status import EnumNodeHealthStatus
from omnibase_core.mixins.mixin_health_check import MixinHealthCheck
from omnibase_core.models.health.model_health_issue import ModelHealthIssue
from omnibase_core.models.health.model_health_status import ModelHealthStatus


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
        assert result.status == "healthy"
        assert result.health_score == 1.0

    def test_health_check_with_custom_check_healthy(self):
        """Test health check with custom check returning healthy."""

        def custom_check():
            return ModelHealthStatus.create_healthy(score=1.0)

        node = TestNode()
        node.custom_checks = [custom_check]

        result = node.health_check()

        assert result.status == "healthy"
        assert result.health_score == 1.0

    def test_health_check_with_custom_check_unhealthy(self):
        """Test health check with custom check returning unhealthy."""

        def custom_check():
            return ModelHealthStatus.create_unhealthy(
                score=0.2,
                issues=[
                    ModelHealthIssue.create_connectivity_issue(
                        message="Custom check failed",
                        severity="high",
                    )
                ],
            )

        node = TestNode()
        node.custom_checks = [custom_check]

        result = node.health_check()

        assert result.status == "unhealthy"
        assert len(result.issues) > 0
        assert any("Custom check failed" in issue.message for issue in result.issues)

    def test_health_check_with_custom_check_degraded(self):
        """Test health check with custom check returning degraded."""

        def custom_check():
            return ModelHealthStatus.create_degraded(
                score=0.6,
                issues=[
                    ModelHealthIssue.create_performance_issue(
                        message="Custom check degraded",
                        severity="medium",
                    )
                ],
            )

        node = TestNode()
        node.custom_checks = [custom_check]

        result = node.health_check()

        assert result.status == "degraded"
        assert len(result.issues) > 0
        assert any("Custom check degraded" in issue.message for issue in result.issues)

    def test_health_check_with_multiple_checks_all_healthy(self):
        """Test health check with multiple checks, all healthy."""

        def check1():
            return ModelHealthStatus.create_healthy(score=1.0)

        def check2():
            return ModelHealthStatus.create_healthy(score=1.0)

        node = TestNode()
        node.custom_checks = [check1, check2]

        result = node.health_check()

        assert result.status == "healthy"
        assert result.health_score == 1.0

    def test_health_check_with_multiple_checks_one_fails(self):
        """Test health check with multiple checks, one fails."""

        def check1():
            return ModelHealthStatus.create_healthy(score=1.0)

        def check2():
            return ModelHealthStatus.create_unhealthy(
                score=0.2,
                issues=[
                    ModelHealthIssue.create_connectivity_issue(
                        message="Check 2 failed",
                        severity="high",
                    )
                ],
            )

        node = TestNode()
        node.custom_checks = [check1, check2]

        result = node.health_check()

        assert result.status == "unhealthy"

    def test_health_check_with_exception_in_check(self):
        """Test health check when custom check raises exception."""

        def failing_check():
            raise RuntimeError("Check failed with exception")

        node = TestNode()
        node.custom_checks = [failing_check]

        result = node.health_check()

        assert result.status == "unhealthy"
        assert len(result.issues) > 0

    def test_health_check_priority_unhealthy_over_degraded(self):
        """Test that UNHEALTHY status takes priority over DEGRADED."""

        def check1():
            return ModelHealthStatus.create_degraded(
                score=0.6,
                issues=[
                    ModelHealthIssue.create_performance_issue(
                        message="Check 1 degraded",
                        severity="medium",
                    )
                ],
            )

        def check2():
            return ModelHealthStatus.create_unhealthy(
                score=0.2,
                issues=[
                    ModelHealthIssue.create_connectivity_issue(
                        message="Check 2 unhealthy",
                        severity="high",
                    )
                ],
            )

        node = TestNode()
        node.custom_checks = [check1, check2]

        result = node.health_check()

        assert result.status == "unhealthy"

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_health_check_async_basic(self):
        """Test async health check with no custom checks."""
        node = TestNode()

        result = await node.health_check_async()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == "healthy"
        assert result.health_score == 1.0

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_health_check_async_with_sync_check(self):
        """Test async health check with synchronous custom check."""

        def sync_check():
            return ModelHealthStatus.create_healthy(score=1.0)

        node = TestNode()
        node.custom_checks = [sync_check]

        result = await node.health_check_async()

        assert result.status == "healthy"
        assert result.health_score == 1.0

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_health_check_async_with_async_check(self):
        """Test async health check with asynchronous custom check."""

        async def async_check():
            await asyncio.sleep(0.01)  # Simulate async work
            return ModelHealthStatus.create_healthy(score=1.0)

        node = TestNode()
        node.custom_checks = [async_check]

        result = await node.health_check_async()

        assert result.status == "healthy"
        assert result.health_score == 1.0

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_health_check_async_with_mixed_checks(self):
        """Test async health check with both sync and async checks."""

        def sync_check():
            return ModelHealthStatus.create_healthy(score=1.0)

        async def async_check():
            await asyncio.sleep(0.01)
            return ModelHealthStatus.create_healthy(score=1.0)

        node = TestNode()
        node.custom_checks = [sync_check, async_check]

        result = await node.health_check_async()

        assert result.status == "healthy"
        assert result.health_score == 1.0

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_health_check_async_with_exception(self):
        """Test async health check when check raises exception."""

        async def failing_check():
            raise RuntimeError("Async check failed")

        node = TestNode()
        node.custom_checks = [failing_check]

        result = await node.health_check_async()

        assert result.status == "unhealthy"

    def test_check_dependency_health_available(self):
        """Test check_dependency_health with available dependency."""
        node = TestNode()

        def check_func():
            return True

        result = node.check_dependency_health("test_dependency", check_func)

        assert isinstance(result, ModelHealthStatus)
        assert result.status == "healthy"
        assert result.health_score == 1.0

    def test_check_dependency_health_unavailable(self):
        """Test check_dependency_health with unavailable dependency."""
        node = TestNode()

        def check_func():
            return False

        result = node.check_dependency_health("test_dependency", check_func)

        assert isinstance(result, ModelHealthStatus)
        assert result.status == "unhealthy"
        assert len(result.issues) > 0
        assert any("test_dependency" in issue.message for issue in result.issues)
        assert any("unavailable" in issue.message for issue in result.issues)

    def test_check_dependency_health_with_exception(self):
        """Test check_dependency_health when check function raises exception."""
        node = TestNode()

        def check_func():
            raise ConnectionError("Cannot connect to dependency")

        result = node.check_dependency_health("test_dependency", check_func)

        assert isinstance(result, ModelHealthStatus)
        assert result.status == "unhealthy"
        assert len(result.issues) > 0
        assert any("test_dependency" in issue.message for issue in result.issues)
        assert any("failed" in issue.message.lower() for issue in result.issues)

    def test_health_check_with_invalid_return_type(self):
        """Test health check when custom check returns invalid type."""

        def invalid_check():
            return "not a health status object"

        node = TestNode()
        node.custom_checks = [invalid_check]

        result = node.health_check()

        # Should handle gracefully and return unhealthy
        assert result.status == "unhealthy"

    def test_health_check_with_async_check_in_sync_context(self):
        """Test health check when async check is called in sync context."""

        async def async_check():
            return ModelHealthStatus.create_healthy(score=1.0)

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
            return ModelHealthStatus.create_unhealthy(
                score=0.2,
                issues=[
                    ModelHealthIssue.create_connectivity_issue(
                        message="Check 3 unhealthy",
                        severity="high",
                    )
                ],
            )

        node = TestNode()
        node.custom_checks = [check1, check2, check3]

        result = node.health_check()

        assert result.status == "unhealthy"
        assert len(result.issues) > 0

    def test_get_health_checks_default(self):
        """Test get_health_checks default implementation."""
        mixin = MixinHealthCheck()

        checks = mixin.get_health_checks()

        assert isinstance(checks, list)
        assert len(checks) == 0

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_health_check_async_invalid_return_type(self):
        """Test async health check with invalid return type."""

        async def invalid_check():
            return "not a health status"

        node = TestNode()
        node.custom_checks = [invalid_check]

        result = await node.health_check_async()

        assert result.status == "unhealthy"

    def test_check_dependency_health_with_none_check_result(self):
        """Test check_dependency_health when check returns None."""
        node = TestNode()

        def check_func():
            return None

        result = node.check_dependency_health("test_dependency", check_func)

        # Should treat None as falsy/unhealthy
        assert result.status == "unhealthy"

    def test_check_dependency_health_with_truthy_values(self):
        """Test check_dependency_health with various truthy values."""
        node = TestNode()

        test_cases = [
            (True, "healthy"),
            (1, "healthy"),
            ("yes", "healthy"),
            ([1, 2], "healthy"),
        ]

        for value, expected_status in test_cases:

            def check_func(_value=value):
                return _value

            result = node.check_dependency_health("test_dependency", check_func)
            assert result.status == expected_status

    def test_check_dependency_health_with_falsy_values(self):
        """Test check_dependency_health with various falsy values."""
        node = TestNode()

        test_cases = [False, 0, "", [], None]

        for value in test_cases:

            def check_func(_value=value):
                return _value

            result = node.check_dependency_health("test_dependency", check_func)
            assert result.status == "unhealthy"
