"""Tests for ModelHealthStatus."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.health.model_health_issue import ModelHealthIssue
from omnibase_core.models.health.model_health_metric import ModelHealthMetric
from omnibase_core.models.health.model_health_status import ModelHealthStatus


class TestModelHealthStatusBasics:
    """Test basic ModelHealthStatus functionality."""

    def test_basic_initialization(self):
        """Test basic health status initialization."""
        status = ModelHealthStatus(status="healthy", health_score=1.0)

        assert status.status == "healthy"
        assert status.health_score == 1.0
        assert status.subsystem_health == {}
        assert status.metrics == []
        assert status.issues == []
        assert status.check_count == 0

    def test_initialization_with_metrics(self):
        """Test initialization with metrics."""
        metric1 = ModelHealthMetric(
            metric_name="cpu_usage", current_value=50.0, unit="%"
        )
        metric2 = ModelHealthMetric(
            metric_name="memory_usage", current_value=60.0, unit="%"
        )

        status = ModelHealthStatus(
            status="healthy", health_score=0.9, metrics=[metric1, metric2]
        )

        assert len(status.metrics) == 2
        assert status.metrics[0].metric_name == "cpu_usage"
        assert status.metrics[1].metric_name == "memory_usage"

    def test_initialization_with_issues(self):
        """Test initialization with issues."""
        issue1 = ModelHealthIssue(
            issue_id=uuid4(),
            severity="high",
            category="performance",
            message="High CPU usage",
            first_detected=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )

        status = ModelHealthStatus(status="degraded", health_score=0.6, issues=[issue1])

        assert len(status.issues) == 1
        assert status.issues[0].severity == "high"


class TestModelHealthStatusValidation:
    """Test ModelHealthStatus validation."""

    def test_status_pattern_validation(self):
        """Test status pattern validation."""
        # Valid statuses
        ModelHealthStatus(status="healthy", health_score=1.0)
        ModelHealthStatus(status="degraded", health_score=0.5)
        ModelHealthStatus(status="unhealthy", health_score=0.2)
        ModelHealthStatus(status="unknown", health_score=0.0)

        # Invalid status
        with pytest.raises(ValidationError):
            ModelHealthStatus(status="invalid_status", health_score=1.0)

    def test_health_score_range_validation(self):
        """Test health score range validation."""
        # Valid scores
        ModelHealthStatus(status="healthy", health_score=0.0)
        ModelHealthStatus(status="healthy", health_score=0.5)
        ModelHealthStatus(status="healthy", health_score=1.0)

        # Invalid scores
        with pytest.raises(ValidationError):
            ModelHealthStatus(status="healthy", health_score=-0.1)
        with pytest.raises(ValidationError):
            ModelHealthStatus(status="healthy", health_score=1.1)

    def test_check_duration_validation(self):
        """Test check_duration_ms validation."""
        # Valid durations
        ModelHealthStatus(status="healthy", health_score=1.0, check_duration_ms=0)
        ModelHealthStatus(status="healthy", health_score=1.0, check_duration_ms=1000)

        # Invalid durations
        with pytest.raises(ValidationError):
            ModelHealthStatus(status="healthy", health_score=1.0, check_duration_ms=-1)

    def test_uptime_validation(self):
        """Test uptime_seconds validation."""
        # Valid uptimes
        ModelHealthStatus(status="healthy", health_score=1.0, uptime_seconds=0)
        ModelHealthStatus(status="healthy", health_score=1.0, uptime_seconds=3600)

        # Invalid uptimes
        with pytest.raises(ValidationError):
            ModelHealthStatus(status="healthy", health_score=1.0, uptime_seconds=-1)


class TestModelHealthStatusHealthChecking:
    """Test health checking methods."""

    def test_is_healthy_default_threshold(self):
        """Test is_healthy with default threshold."""
        status = ModelHealthStatus(status="healthy", health_score=0.8)
        assert status.is_healthy() is True

        status = ModelHealthStatus(status="healthy", health_score=0.6)
        assert status.is_healthy() is False

    def test_is_healthy_custom_threshold(self):
        """Test is_healthy with custom threshold."""
        status = ModelHealthStatus(status="healthy", health_score=0.6)

        assert status.is_healthy(threshold=0.5) is True
        assert status.is_healthy(threshold=0.7) is False

    def test_is_degraded_default(self):
        """Test is_degraded with default threshold."""
        status = ModelHealthStatus(status="degraded", health_score=0.6)
        assert status.is_degraded() is True

        status = ModelHealthStatus(status="degraded", health_score=0.8)
        assert status.is_degraded() is False

        status = ModelHealthStatus(status="degraded", health_score=0.4)
        assert status.is_degraded() is False

    def test_is_degraded_custom_threshold(self):
        """Test is_degraded with custom threshold."""
        status = ModelHealthStatus(status="degraded", health_score=0.4)

        assert status.is_degraded(degraded_threshold=0.3) is True
        assert status.is_degraded(degraded_threshold=0.5) is False

    def test_is_critical_low_score(self):
        """Test is_critical with low health score."""
        status = ModelHealthStatus(status="healthy", health_score=0.2)
        assert status.is_critical() is True

    def test_is_critical_with_critical_issues(self):
        """Test is_critical with critical issues."""
        issue = ModelHealthIssue(
            issue_id=uuid4(),
            severity="critical",
            category="security",
            message="Critical security issue",
            first_detected=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )

        status = ModelHealthStatus(status="degraded", health_score=0.8, issues=[issue])
        assert status.is_critical() is True

    def test_is_critical_unhealthy_status(self):
        """Test is_critical with unhealthy status."""
        status = ModelHealthStatus(status="unhealthy", health_score=0.5)
        assert status.is_critical() is True


class TestModelHealthStatusIssueManagement:
    """Test issue management methods."""

    def test_get_critical_issues(self):
        """Test get_critical_issues method."""
        critical_issue = ModelHealthIssue(
            issue_id=uuid4(),
            severity="critical",
            category="security",
            message="Critical issue",
            first_detected=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )
        high_issue = ModelHealthIssue(
            issue_id=uuid4(),
            severity="high",
            category="performance",
            message="High issue",
            first_detected=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )

        status = ModelHealthStatus(
            status="unhealthy",
            health_score=0.3,
            issues=[critical_issue, high_issue],
        )

        critical_issues = status.get_critical_issues()
        assert len(critical_issues) == 1
        assert critical_issues[0].severity == "critical"

    def test_get_high_issues(self):
        """Test get_high_issues method."""
        high_issue1 = ModelHealthIssue(
            issue_id=uuid4(),
            severity="high",
            category="performance",
            message="High issue 1",
            first_detected=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )
        high_issue2 = ModelHealthIssue(
            issue_id=uuid4(),
            severity="high",
            category="resource",
            message="High issue 2",
            first_detected=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )
        medium_issue = ModelHealthIssue(
            issue_id=uuid4(),
            severity="medium",
            category="configuration",
            message="Medium issue",
            first_detected=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )

        status = ModelHealthStatus(
            status="degraded",
            health_score=0.5,
            issues=[high_issue1, high_issue2, medium_issue],
        )

        high_issues = status.get_high_issues()
        assert len(high_issues) == 2
        assert all(issue.severity == "high" for issue in high_issues)


class TestModelHealthStatusMetricManagement:
    """Test metric management methods."""

    def test_get_metric_by_name_found(self):
        """Test get_metric_by_name when metric exists."""
        cpu_metric = ModelHealthMetric(
            metric_name="cpu_usage", current_value=75.0, unit="%"
        )
        memory_metric = ModelHealthMetric(
            metric_name="memory_usage", current_value=60.0, unit="%"
        )

        status = ModelHealthStatus(
            status="healthy",
            health_score=0.9,
            metrics=[cpu_metric, memory_metric],
        )

        found_metric = status.get_metric_by_name("cpu_usage")
        assert found_metric is not None
        assert found_metric.metric_name == "cpu_usage"
        assert found_metric.current_value == 75.0

    def test_get_metric_by_name_not_found(self):
        """Test get_metric_by_name when metric doesn't exist."""
        cpu_metric = ModelHealthMetric(
            metric_name="cpu_usage", current_value=75.0, unit="%"
        )

        status = ModelHealthStatus(
            status="healthy", health_score=0.9, metrics=[cpu_metric]
        )

        found_metric = status.get_metric_by_name("nonexistent")
        assert found_metric is None


class TestModelHealthStatusSubsystems:
    """Test subsystem health management."""

    def test_subsystem_health_tracking(self):
        """Test tracking subsystem health."""
        database_health = ModelHealthStatus(status="healthy", health_score=0.95)
        cache_health = ModelHealthStatus(status="degraded", health_score=0.6)

        status = ModelHealthStatus(
            status="degraded",
            health_score=0.75,
            subsystem_health={"database": database_health, "cache": cache_health},
        )

        assert len(status.subsystem_health) == 2
        assert status.subsystem_health["database"].health_score == 0.95
        assert status.subsystem_health["cache"].health_score == 0.6

    def test_get_subsystem_health_summary(self):
        """Test get_subsystem_health_summary method."""
        database_health = ModelHealthStatus(status="healthy", health_score=0.95)
        cache_health = ModelHealthStatus(status="degraded", health_score=0.6)
        api_health = ModelHealthStatus(status="unhealthy", health_score=0.3)

        status = ModelHealthStatus(
            status="degraded",
            health_score=0.6,
            subsystem_health={
                "database": database_health,
                "cache": cache_health,
                "api": api_health,
            },
        )

        summary = status.get_subsystem_health_summary()
        assert summary["database"] == "healthy"
        assert summary["cache"] == "degraded"
        assert summary["api"] == "unhealthy"


class TestModelHealthStatusScoreCalculation:
    """Test health score calculation."""

    def test_calculate_overall_health_score_no_subsystems(self):
        """Test score calculation without subsystems."""
        status = ModelHealthStatus(status="healthy", health_score=0.9)

        calculated_score = status.calculate_overall_health_score()
        assert calculated_score == 0.9

    def test_calculate_overall_health_score_with_subsystems(self):
        """Test score calculation with subsystems."""
        sub1 = ModelHealthStatus(status="healthy", health_score=0.9)
        sub2 = ModelHealthStatus(status="healthy", health_score=0.8)

        status = ModelHealthStatus(
            status="healthy",
            health_score=0.85,
            subsystem_health={"sub1": sub1, "sub2": sub2},
        )

        calculated_score = status.calculate_overall_health_score()
        # Should average base score with subsystem scores
        expected = (0.85 + (0.9 + 0.8) / 2) / 2
        assert abs(calculated_score - expected) < 0.01

    def test_calculate_overall_health_score_with_issues(self):
        """Test score calculation with issues."""
        critical_issue = ModelHealthIssue(
            issue_id=uuid4(),
            severity="critical",
            category="security",
            message="Critical",
            first_detected=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )
        high_issue = ModelHealthIssue(
            issue_id=uuid4(),
            severity="high",
            category="performance",
            message="High",
            first_detected=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )

        status = ModelHealthStatus(
            status="degraded",
            health_score=1.0,
            issues=[critical_issue, high_issue],
        )

        calculated_score = status.calculate_overall_health_score()
        # Should be reduced by 0.3 (critical) + 0.1 (high) = 0.4
        assert calculated_score <= 0.6


class TestModelHealthStatusAttentionNeeded:
    """Test needs_attention method."""

    def test_needs_attention_critical(self):
        """Test needs_attention for critical status."""
        status = ModelHealthStatus(status="unhealthy", health_score=0.2)
        assert status.needs_attention() is True

    def test_needs_attention_critical_issues(self):
        """Test needs_attention with critical issues."""
        critical_issue = ModelHealthIssue(
            issue_id=uuid4(),
            severity="critical",
            category="security",
            message="Critical",
            first_detected=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )

        status = ModelHealthStatus(
            status="degraded", health_score=0.8, issues=[critical_issue]
        )
        assert status.needs_attention() is True

    def test_needs_attention_many_high_issues(self):
        """Test needs_attention with many high issues."""
        high_issues = [
            ModelHealthIssue(
                issue_id=uuid4(),
                severity="high",
                category="performance",
                message=f"Issue {i}",
                first_detected=datetime.now(UTC),
                last_seen=datetime.now(UTC),
            )
            for i in range(4)
        ]

        status = ModelHealthStatus(
            status="degraded", health_score=0.7, issues=high_issues
        )
        assert status.needs_attention() is True

    def test_needs_attention_low_score(self):
        """Test needs_attention with low health score."""
        status = ModelHealthStatus(status="degraded", health_score=0.4)
        assert status.needs_attention() is True

    def test_needs_attention_healthy(self):
        """Test needs_attention for healthy status."""
        status = ModelHealthStatus(status="healthy", health_score=0.9)
        assert status.needs_attention() is False


class TestModelHealthStatusSummary:
    """Test health summary generation."""

    def test_get_health_summary_critical(self):
        """Test health summary for critical status."""
        critical_issue = ModelHealthIssue(
            issue_id=uuid4(),
            severity="critical",
            category="security",
            message="Critical",
            first_detected=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )

        status = ModelHealthStatus(
            status="unhealthy", health_score=0.2, issues=[critical_issue]
        )

        summary = status.get_health_summary()
        assert "CRITICAL" in summary
        assert "0.2" in summary or "20" in summary

    def test_get_health_summary_degraded(self):
        """Test health summary for degraded status."""
        status = ModelHealthStatus(status="degraded", health_score=0.6)

        summary = status.get_health_summary()
        assert "DEGRADED" in summary

    def test_get_health_summary_healthy(self):
        """Test health summary for healthy status."""
        status = ModelHealthStatus(status="healthy", health_score=0.9)

        summary = status.get_health_summary()
        assert "HEALTHY" in summary


class TestModelHealthStatusFactoryMethods:
    """Test factory methods."""

    def test_create_healthy(self):
        """Test create_healthy factory method."""
        status = ModelHealthStatus.create_healthy(score=0.95)

        assert status.status == "healthy"
        assert status.health_score == 0.95
        assert status.check_count == 1
        assert len(status.issues) == 0

    def test_create_degraded(self):
        """Test create_degraded factory method."""
        issue = ModelHealthIssue(
            issue_id=uuid4(),
            severity="medium",
            category="performance",
            message="Slow",
            first_detected=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )

        status = ModelHealthStatus.create_degraded(score=0.6, issues=[issue])

        assert status.status == "degraded"
        assert status.health_score == 0.6
        assert status.check_count == 1
        assert len(status.issues) == 1

    def test_create_unhealthy(self):
        """Test create_unhealthy factory method."""
        issue = ModelHealthIssue(
            issue_id=uuid4(),
            severity="critical",
            category="security",
            message="Critical",
            first_detected=datetime.now(UTC),
            last_seen=datetime.now(UTC),
        )

        status = ModelHealthStatus.create_unhealthy(score=0.2, issues=[issue])

        assert status.status == "unhealthy"
        assert status.health_score == 0.2
        assert status.check_count == 1
        assert len(status.issues) == 1
