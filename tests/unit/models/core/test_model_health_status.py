# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelHealthStatus.

Comprehensive tests for the rich health status model including health scoring,
subsystem tracking, issues management, and metrics collection.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from omnibase_core.models.health.model_health_issue import ModelHealthIssue
from omnibase_core.models.health.model_health_metric import ModelHealthMetric
from omnibase_core.models.health.model_health_status import ModelHealthStatus
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


@pytest.mark.unit
class TestModelHealthStatus:
    """Test suite for ModelHealthStatus."""

    def test_initialization_with_required_fields(self):
        """Test initialization with required fields only."""
        status = ModelHealthStatus(status="healthy", health_score=1.0)

        assert status.status == "healthy"
        assert status.health_score == 1.0
        assert status.subsystem_health == {}
        assert status.metrics == []
        assert status.issues == []
        assert isinstance(status.last_check, datetime)
        assert status.next_check is None
        assert status.check_duration_ms is None
        assert status.check_count == 0
        assert status.uptime_seconds is None
        assert status.metadata is None

    def test_initialization_with_all_fields(self):
        """Test initialization with all fields."""
        now = datetime.now(UTC)
        next_check = datetime.now(UTC)

        metric = ModelHealthMetric.create_cpu_metric(value=45.5)

        now_utc = datetime.now(UTC)
        issue = ModelHealthIssue(
            issue_id=uuid4(),
            severity="high",
            category="performance",
            message="High CPU usage",
            first_detected=now_utc,
            last_seen=now_utc,
        )

        status = ModelHealthStatus(
            status="degraded",
            health_score=0.6,
            metrics=[metric],
            issues=[issue],
            last_check=now,
            next_check=next_check,
            check_duration_ms=150,
            check_count=5,
            uptime_seconds=3600,
        )

        assert status.status == "degraded"
        assert status.health_score == 0.6
        assert len(status.metrics) == 1
        assert len(status.issues) == 1
        assert status.last_check == now
        assert status.next_check == next_check
        assert status.check_duration_ms == 150
        assert status.check_count == 5
        assert status.uptime_seconds == 3600

    def test_different_health_statuses(self):
        """Test different health status values."""
        # Healthy
        healthy = ModelHealthStatus(status="healthy", health_score=1.0)
        assert healthy.status == "healthy"

        # Degraded
        degraded = ModelHealthStatus(status="degraded", health_score=0.6)
        assert degraded.status == "degraded"

        # Unhealthy
        unhealthy = ModelHealthStatus(status="unhealthy", health_score=0.2)
        assert unhealthy.status == "unhealthy"

        # Unknown
        unknown = ModelHealthStatus(status="unknown", health_score=0.5)
        assert unknown.status == "unknown"

        # Custom
        custom = ModelHealthStatus(status="custom", health_score=0.8)
        assert custom.status == "custom"

    def test_health_score_precision(self):
        """Test health_score accepts precise float values."""
        status = ModelHealthStatus(status="healthy", health_score=0.876543)

        assert status.health_score == 0.876543
        assert isinstance(status.health_score, float)

    def test_health_score_boundaries(self):
        """Test health_score validates boundaries (0.0-1.0)."""
        # Valid boundaries
        min_status = ModelHealthStatus(status="unhealthy", health_score=0.0)
        assert min_status.health_score == 0.0

        max_status = ModelHealthStatus(status="healthy", health_score=1.0)
        assert max_status.health_score == 1.0

        # Invalid values should raise ValidationError
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelHealthStatus(status="healthy", health_score=-0.1)

        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelHealthStatus(status="healthy", health_score=1.1)

    def test_uptime_seconds_precision(self):
        """Test uptime_seconds accepts integer values."""
        status = ModelHealthStatus(
            status="healthy", health_score=1.0, uptime_seconds=3661
        )

        assert status.uptime_seconds == 3661
        assert isinstance(status.uptime_seconds, int)

    def test_check_duration_ms_validation(self):
        """Test check_duration_ms accepts non-negative integers."""
        status = ModelHealthStatus(
            status="healthy", health_score=1.0, check_duration_ms=150
        )

        assert status.check_duration_ms == 150

        # Negative values should raise ValidationError
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelHealthStatus(status="healthy", health_score=1.0, check_duration_ms=-1)

    def test_check_count_validation(self):
        """Test check_count validates non-negative integers."""
        status = ModelHealthStatus(status="healthy", health_score=1.0, check_count=10)

        assert status.check_count == 10

        # Negative values should raise ValidationError
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelHealthStatus(status="healthy", health_score=1.0, check_count=-1)

    def test_uptime_seconds_validation(self):
        """Test uptime_seconds validates non-negative integers."""
        status = ModelHealthStatus(
            status="healthy", health_score=1.0, uptime_seconds=1000
        )

        assert status.uptime_seconds == 1000

        # Negative values should raise ValidationError
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelHealthStatus(status="healthy", health_score=1.0, uptime_seconds=-1)

    def test_serialization(self):
        """Test model serialization."""
        status = ModelHealthStatus(
            status="healthy",
            health_score=0.95,
            check_count=5,
            uptime_seconds=3600,
        )

        data = status.model_dump()

        assert data["status"] == "healthy"
        assert data["health_score"] == 0.95
        assert data["check_count"] == 5
        assert data["uptime_seconds"] == 3600
        assert "last_check" in data
        assert "subsystem_health" in data
        assert "metrics" in data
        assert "issues" in data

    def test_deserialization(self):
        """Test model deserialization from dict."""
        data = {
            "status": "degraded",
            "health_score": 0.7,
            "check_count": 3,
            "uptime_seconds": 1800,
        }

        status = ModelHealthStatus(**data)

        assert status.status == "degraded"
        assert status.health_score == 0.7
        assert status.check_count == 3
        assert status.uptime_seconds == 1800

    def test_zero_values(self):
        """Test handling of zero values."""
        status = ModelHealthStatus(
            status="healthy",
            health_score=0.0,
            check_count=0,
            uptime_seconds=0,
            check_duration_ms=0,
        )

        assert status.health_score == 0.0
        assert status.check_count == 0
        assert status.uptime_seconds == 0
        assert status.check_duration_ms == 0

    def test_large_values(self):
        """Test handling of large values."""
        status = ModelHealthStatus(
            status="healthy",
            health_score=1.0,
            check_count=999999,
            uptime_seconds=999999999,
            check_duration_ms=999999,
        )

        assert status.check_count == 999999
        assert status.uptime_seconds == 999999999
        assert status.check_duration_ms == 999999

    def test_is_healthy_method(self):
        """Test is_healthy method with different thresholds."""
        # Healthy status
        healthy = ModelHealthStatus(status="healthy", health_score=0.85)
        assert healthy.is_healthy()  # Default threshold 0.7
        assert healthy.is_healthy(threshold=0.8)
        assert not healthy.is_healthy(threshold=0.9)

        # Unhealthy status
        unhealthy = ModelHealthStatus(status="unhealthy", health_score=0.5)
        assert not unhealthy.is_healthy()

    def test_is_degraded_method(self):
        """Test is_degraded method."""
        # Degraded status
        degraded = ModelHealthStatus(status="degraded", health_score=0.6)
        assert degraded.is_degraded()

        # Healthy status
        healthy = ModelHealthStatus(status="healthy", health_score=0.9)
        assert not healthy.is_degraded()

        # Unhealthy status
        unhealthy = ModelHealthStatus(status="unhealthy", health_score=0.3)
        assert not unhealthy.is_degraded()

    def test_is_critical_method(self):
        """Test is_critical method."""
        # Critical due to low score
        critical_score = ModelHealthStatus(status="unhealthy", health_score=0.2)
        assert critical_score.is_critical()

        # Critical due to status
        critical_status = ModelHealthStatus(status="unhealthy", health_score=0.5)
        assert critical_status.is_critical()

        # Critical due to critical issue
        now_utc = datetime.now(UTC)
        issue = ModelHealthIssue(
            issue_id=uuid4(),
            severity="critical",
            category="security",
            message="System failure",
            first_detected=now_utc,
            last_seen=now_utc,
        )
        critical_issue = ModelHealthStatus(
            status="degraded", health_score=0.5, issues=[issue]
        )
        assert critical_issue.is_critical()

        # Not critical
        healthy = ModelHealthStatus(status="healthy", health_score=0.9)
        assert not healthy.is_critical()

    def test_get_critical_issues(self):
        """Test get_critical_issues method."""
        now_utc = datetime.now(UTC)
        critical_issue = ModelHealthIssue(
            issue_id=uuid4(),
            severity="critical",
            category="security",
            message="Critical failure",
            first_detected=now_utc,
            last_seen=now_utc,
        )

        high_issue = ModelHealthIssue(
            issue_id=uuid4(),
            severity="high",
            category="performance",
            message="High latency",
            first_detected=now_utc,
            last_seen=now_utc,
        )

        status = ModelHealthStatus(
            status="unhealthy", health_score=0.3, issues=[critical_issue, high_issue]
        )

        critical_issues = status.get_critical_issues()
        assert len(critical_issues) == 1
        assert critical_issues[0].severity == "critical"

    def test_get_high_issues(self):
        """Test get_high_issues method."""
        now_utc = datetime.now(UTC)
        high_issue = ModelHealthIssue(
            issue_id=uuid4(),
            severity="high",
            category="performance",
            message="High latency",
            first_detected=now_utc,
            last_seen=now_utc,
        )

        medium_issue = ModelHealthIssue(
            issue_id=uuid4(),
            severity="medium",
            category="resource",
            message="Memory leak",
            first_detected=now_utc,
            last_seen=now_utc,
        )

        status = ModelHealthStatus(
            status="degraded", health_score=0.6, issues=[high_issue, medium_issue]
        )

        high_issues = status.get_high_issues()
        assert len(high_issues) == 1
        assert high_issues[0].severity == "high"

    def test_get_metric_by_name(self):
        """Test get_metric_by_name method."""
        cpu_metric = ModelHealthMetric.create_cpu_metric(value=45.5)
        memory_metric = ModelHealthMetric.create_memory_metric(value=75.0)

        status = ModelHealthStatus(
            status="healthy", health_score=0.9, metrics=[cpu_metric, memory_metric]
        )

        found_metric = status.get_metric_by_name("cpu_usage")
        assert found_metric is not None
        assert found_metric.current_value == 45.5

        not_found = status.get_metric_by_name("nonexistent")
        assert not_found is None

    def test_subsystem_health(self):
        """Test subsystem health tracking."""
        db_health = ModelHealthStatus(status="healthy", health_score=0.95)
        cache_health = ModelHealthStatus(status="degraded", health_score=0.6)

        main_status = ModelHealthStatus(
            status="degraded",
            health_score=0.75,
            subsystem_health={"database": db_health, "cache": cache_health},
        )

        assert len(main_status.subsystem_health) == 2
        assert main_status.subsystem_health["database"].health_score == 0.95
        assert main_status.subsystem_health["cache"].health_score == 0.6

    def test_get_subsystem_health_summary(self):
        """Test get_subsystem_health_summary method."""
        db_health = ModelHealthStatus(status="healthy", health_score=0.95)
        api_health = ModelHealthStatus(status="degraded", health_score=0.6)

        main_status = ModelHealthStatus(
            status="degraded",
            health_score=0.75,
            subsystem_health={"database": db_health, "api": api_health},
        )

        summary = main_status.get_subsystem_health_summary()
        assert summary == {"database": "healthy", "api": "degraded"}

    def test_needs_attention_method(self):
        """Test needs_attention method."""
        # Needs attention due to low score
        low_score = ModelHealthStatus(status="degraded", health_score=0.4)
        assert low_score.needs_attention()

        # Needs attention due to critical issue
        now_utc = datetime.now(UTC)
        critical_issue = ModelHealthIssue(
            issue_id=uuid4(),
            severity="critical",
            category="security",
            message="Critical failure",
            first_detected=now_utc,
            last_seen=now_utc,
        )
        with_critical = ModelHealthStatus(
            status="degraded", health_score=0.7, issues=[critical_issue]
        )
        assert with_critical.needs_attention()

        # Needs attention due to many high issues
        high_issues = [
            ModelHealthIssue(
                issue_id=uuid4(),
                severity="high",
                category="performance",
                message=f"Issue {i}",
                first_detected=now_utc,
                last_seen=now_utc,
            )
            for i in range(4)
        ]
        with_many_high = ModelHealthStatus(
            status="degraded", health_score=0.7, issues=high_issues
        )
        assert with_many_high.needs_attention()

        # Doesn't need attention
        healthy = ModelHealthStatus(status="healthy", health_score=0.9)
        assert not healthy.needs_attention()

    def test_get_health_summary(self):
        """Test get_health_summary method."""
        # Healthy
        healthy = ModelHealthStatus(status="healthy", health_score=0.9)
        summary = healthy.get_health_summary()
        assert "HEALTHY" in summary
        assert "90" in summary

        # Degraded
        degraded = ModelHealthStatus(status="degraded", health_score=0.6)
        summary = degraded.get_health_summary()
        assert "DEGRADED" in summary

        # Critical
        critical = ModelHealthStatus(status="unhealthy", health_score=0.2)
        summary = critical.get_health_summary()
        assert "CRITICAL" in summary

    def test_create_healthy_factory(self):
        """Test create_healthy class method."""
        status = ModelHealthStatus.create_healthy()

        assert status.status == "healthy"
        assert status.health_score == 1.0
        assert status.check_count == 1

        # Custom score
        custom = ModelHealthStatus.create_healthy(score=0.85)
        assert custom.health_score == 0.85

    def test_create_degraded_factory(self):
        """Test create_degraded class method."""
        status = ModelHealthStatus.create_degraded()

        assert status.status == "degraded"
        assert status.health_score == 0.6
        assert status.check_count == 1

        # With issues
        issue = ModelHealthIssue.create_performance_issue(
            message="Slow response", severity="medium"
        )
        with_issues = ModelHealthStatus.create_degraded(issues=[issue])
        assert len(with_issues.issues) == 1

    def test_create_unhealthy_factory(self):
        """Test create_unhealthy class method."""
        status = ModelHealthStatus.create_unhealthy()

        assert status.status == "unhealthy"
        assert status.health_score == 0.2
        assert status.check_count == 1

        # With issues
        now_utc = datetime.now(UTC)
        issue = ModelHealthIssue(
            issue_id=uuid4(),
            severity="critical",
            category="security",
            message="System failure",
            first_detected=now_utc,
            last_seen=now_utc,
        )
        with_issues = ModelHealthStatus.create_unhealthy(issues=[issue])
        assert len(with_issues.issues) == 1


@pytest.mark.unit
class TestModelHealthStatusEdgeCases:
    """Edge case tests for ModelHealthStatus."""

    def test_invalid_status_pattern(self):
        """Test that invalid status values raise ValidationError."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelHealthStatus(status="invalid", health_score=0.5)

    def test_model_copy(self):
        """Test model copying."""
        original = ModelHealthStatus(
            status="healthy",
            health_score=0.9,
            check_count=5,
        )

        copy = original.model_copy()

        assert copy.status == original.status
        assert copy.health_score == original.health_score
        assert copy.check_count == original.check_count
        assert copy is not original

    def test_model_copy_deep(self):
        """Test deep model copying."""
        metric = ModelHealthMetric.create_cpu_metric(value=45.5)

        original = ModelHealthStatus(
            status="healthy", health_score=0.9, metrics=[metric]
        )

        copy = original.model_copy(deep=True)

        assert copy.metrics is not original.metrics
        assert len(copy.metrics) == len(original.metrics)

    def test_calculate_overall_health_score_no_subsystems(self):
        """Test calculate_overall_health_score with no subsystems or issues."""
        status = ModelHealthStatus(status="healthy", health_score=0.9)

        calculated = status.calculate_overall_health_score()
        assert calculated == 0.9

    def test_calculate_overall_health_score_with_subsystems(self):
        """Test calculate_overall_health_score with subsystems."""
        sub1 = ModelHealthStatus(status="healthy", health_score=0.9)
        sub2 = ModelHealthStatus(status="degraded", health_score=0.6)

        status = ModelHealthStatus(
            status="degraded",
            health_score=0.8,
            subsystem_health={"sub1": sub1, "sub2": sub2},
        )

        calculated = status.calculate_overall_health_score()
        # Should be average of 0.8 and ((0.9 + 0.6) / 2)
        expected = (0.8 + 0.75) / 2
        assert calculated == expected

    def test_calculate_overall_health_score_with_issues(self):
        """Test calculate_overall_health_score with issues penalties."""
        now_utc = datetime.now(UTC)
        critical_issue = ModelHealthIssue(
            issue_id=uuid4(),
            severity="critical",
            category="security",
            message="Critical failure",
            first_detected=now_utc,
            last_seen=now_utc,
        )

        status = ModelHealthStatus(
            status="unhealthy", health_score=0.8, issues=[critical_issue]
        )

        calculated = status.calculate_overall_health_score()
        # Should be 0.8 - 0.3 (critical penalty) = 0.5
        assert calculated == 0.5
