# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for MixinHealthCheck.get_health_report() (OMN-6606).

Verifies that get_health_report() aggregates health check results
into a dict suitable for dispatch engine health reporting.
"""

import pytest

from omnibase_core.mixins.mixin_health_check import MixinHealthCheck
from omnibase_core.models.health.model_health_status import ModelHealthStatus


class _TestableHealthCheck(MixinHealthCheck):
    """Minimal testable subclass of MixinHealthCheck."""

    def __init__(self, health_checks: list | None = None) -> None:
        super().__init__()
        self._custom_checks = health_checks or []

    def get_health_checks(self) -> list:  # type: ignore[override]
        return self._custom_checks


@pytest.mark.unit
class TestGetHealthReport:
    """Tests for get_health_report()."""

    @pytest.mark.asyncio
    async def test_healthy_report(self) -> None:
        """Report shows healthy status when no custom checks fail."""
        node = _TestableHealthCheck()
        report = await node.get_health_report()

        assert report["status"] == "healthy"
        assert report["health_score"] == 1.0
        assert report["issues"] == []
        assert report["node_class"] == "_TestableHealthCheck"

    @pytest.mark.asyncio
    async def test_report_with_unhealthy_check(self) -> None:
        """Report shows degraded status when a check returns unhealthy."""
        from omnibase_core.models.health.model_health_issue import ModelHealthIssue

        def _failing_check() -> ModelHealthStatus:
            return ModelHealthStatus.create_unhealthy(
                score=0.0,
                issues=[
                    ModelHealthIssue.create_connectivity_issue(
                        message="DB unreachable",
                        severity="critical",
                    )
                ],
            )

        node = _TestableHealthCheck(health_checks=[_failing_check])
        report = await node.get_health_report()

        assert report["health_score"] < 1.0
        assert len(report["issues"]) > 0  # type: ignore[arg-type]
