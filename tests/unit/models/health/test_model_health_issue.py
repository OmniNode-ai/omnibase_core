"""Tests for ModelHealthIssue."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from omnibase_core.models.health.model_health_issue import ModelHealthIssue


class TestModelHealthIssueBasics:
    """Test basic functionality."""

    def test_basic_initialization(self):
        """Test basic issue initialization."""
        issue_id = uuid4()
        first_detected = datetime.now(UTC)
        last_seen = datetime.now(UTC)

        issue = ModelHealthIssue(
            issue_id=issue_id,
            severity="high",
            category="performance",
            message="High CPU usage detected",
            first_detected=first_detected,
            last_seen=last_seen,
        )

        assert issue.issue_id == issue_id
        assert issue.severity == "high"
        assert issue.category == "performance"
        assert issue.message == "High CPU usage detected"
        assert issue.first_detected == first_detected
        assert issue.last_seen == last_seen
        assert issue.count == 1
        assert issue.auto_recoverable is False
        assert issue.recovery_action is None


class TestModelHealthIssueValidation:
    """Test validation."""

    def test_severity_pattern_validation(self):
        """Test severity pattern validation."""
        issue_id = uuid4()
        now = datetime.now(UTC)

        # Valid severities
        ModelHealthIssue(
            issue_id=issue_id,
            severity="low",
            category="performance",
            message="test",
            first_detected=now,
            last_seen=now,
        )
        ModelHealthIssue(
            issue_id=issue_id,
            severity="medium",
            category="performance",
            message="test",
            first_detected=now,
            last_seen=now,
        )
        ModelHealthIssue(
            issue_id=issue_id,
            severity="high",
            category="performance",
            message="test",
            first_detected=now,
            last_seen=now,
        )
        ModelHealthIssue(
            issue_id=issue_id,
            severity="critical",
            category="performance",
            message="test",
            first_detected=now,
            last_seen=now,
        )

        # Invalid severity
        with pytest.raises(Exception):
            ModelHealthIssue(
                issue_id=issue_id,
                severity="invalid",
                category="performance",
                message="test",
                first_detected=now,
                last_seen=now,
            )

    def test_category_pattern_validation(self):
        """Test category pattern validation."""
        issue_id = uuid4()
        now = datetime.now(UTC)

        # Valid categories
        for category in [
            "performance",
            "connectivity",
            "resource",
            "configuration",
            "security",
            "validation",
            "other",
        ]:
            ModelHealthIssue(
                issue_id=issue_id,
                severity="high",
                category=category,
                message="test",
                first_detected=now,
                last_seen=now,
            )

        # Invalid category
        with pytest.raises(Exception):
            ModelHealthIssue(
                issue_id=issue_id,
                severity="high",
                category="invalid",
                message="test",
                first_detected=now,
                last_seen=now,
            )

    def test_count_minimum_validation(self):
        """Test count minimum validation."""
        issue_id = uuid4()
        now = datetime.now(UTC)

        # Valid counts
        ModelHealthIssue(
            issue_id=issue_id,
            severity="high",
            category="performance",
            message="test",
            first_detected=now,
            last_seen=now,
            count=1,
        )
        ModelHealthIssue(
            issue_id=issue_id,
            severity="high",
            category="performance",
            message="test",
            first_detected=now,
            last_seen=now,
            count=100,
        )

        # Invalid count
        with pytest.raises(Exception):
            ModelHealthIssue(
                issue_id=issue_id,
                severity="high",
                category="performance",
                message="test",
                first_detected=now,
                last_seen=now,
                count=0,
            )


class TestModelHealthIssueChecks:
    """Test issue checking methods."""

    def test_is_critical(self):
        """Test is_critical method."""
        issue_id = uuid4()
        now = datetime.now(UTC)

        critical_issue = ModelHealthIssue(
            issue_id=issue_id,
            severity="critical",
            category="security",
            message="Critical security issue",
            first_detected=now,
            last_seen=now,
        )
        assert critical_issue.is_critical() is True

        high_issue = ModelHealthIssue(
            issue_id=issue_id,
            severity="high",
            category="performance",
            message="High performance issue",
            first_detected=now,
            last_seen=now,
        )
        assert high_issue.is_critical() is False

    def test_is_recurring_default_threshold(self):
        """Test is_recurring with default threshold."""
        issue_id = uuid4()
        now = datetime.now(UTC)

        # Below threshold
        issue = ModelHealthIssue(
            issue_id=issue_id,
            severity="high",
            category="performance",
            message="test",
            first_detected=now,
            last_seen=now,
            count=2,
        )
        assert issue.is_recurring() is False

        # At threshold
        issue = ModelHealthIssue(
            issue_id=issue_id,
            severity="high",
            category="performance",
            message="test",
            first_detected=now,
            last_seen=now,
            count=3,
        )
        assert issue.is_recurring() is True

        # Above threshold
        issue = ModelHealthIssue(
            issue_id=issue_id,
            severity="high",
            category="performance",
            message="test",
            first_detected=now,
            last_seen=now,
            count=5,
        )
        assert issue.is_recurring() is True

    def test_is_recurring_custom_threshold(self):
        """Test is_recurring with custom threshold."""
        issue_id = uuid4()
        now = datetime.now(UTC)

        issue = ModelHealthIssue(
            issue_id=issue_id,
            severity="high",
            category="performance",
            message="test",
            first_detected=now,
            last_seen=now,
            count=5,
        )

        assert issue.is_recurring(threshold=6) is False
        assert issue.is_recurring(threshold=5) is True
        assert issue.is_recurring(threshold=4) is True

    def test_get_duration_seconds(self):
        """Test get_duration_seconds method."""
        import time

        issue_id = uuid4()
        first_detected = datetime.now(UTC)
        time.sleep(0.1)  # Small delay
        last_seen = datetime.now(UTC)

        issue = ModelHealthIssue(
            issue_id=issue_id,
            severity="high",
            category="performance",
            message="test",
            first_detected=first_detected,
            last_seen=last_seen,
        )

        duration = issue.get_duration_seconds()
        assert duration >= 0
        assert isinstance(duration, int)


class TestModelHealthIssueFactoryMethods:
    """Test factory methods."""

    def test_create_performance_issue(self):
        """Test performance issue factory."""
        issue = ModelHealthIssue.create_performance_issue(
            message="High CPU usage", severity="high"
        )

        assert isinstance(issue.issue_id, UUID)
        assert issue.severity == "high"
        assert issue.category == "performance"
        assert issue.message == "High CPU usage"
        assert issue.count == 1

    def test_create_performance_issue_default_severity(self):
        """Test performance issue with default severity."""
        issue = ModelHealthIssue.create_performance_issue(message="Slow response")

        assert issue.severity == "medium"
        assert issue.category == "performance"

    def test_create_connectivity_issue(self):
        """Test connectivity issue factory."""
        issue = ModelHealthIssue.create_connectivity_issue(
            message="Connection timeout", severity="critical"
        )

        assert isinstance(issue.issue_id, UUID)
        assert issue.severity == "critical"
        assert issue.category == "connectivity"
        assert issue.message == "Connection timeout"
        assert issue.count == 1

    def test_create_connectivity_issue_default_severity(self):
        """Test connectivity issue with default severity."""
        issue = ModelHealthIssue.create_connectivity_issue(message="Network error")

        assert issue.severity == "high"
        assert issue.category == "connectivity"

    def test_create_resource_issue(self):
        """Test resource issue factory."""
        issue = ModelHealthIssue.create_resource_issue(
            message="Out of memory", severity="critical"
        )

        assert isinstance(issue.issue_id, UUID)
        assert issue.severity == "critical"
        assert issue.category == "resource"
        assert issue.message == "Out of memory"
        assert issue.count == 1

    def test_create_resource_issue_default_severity(self):
        """Test resource issue with default severity."""
        issue = ModelHealthIssue.create_resource_issue(message="Low disk space")

        assert issue.severity == "high"
        assert issue.category == "resource"

    def test_create_configuration_issue(self):
        """Test configuration issue factory."""
        issue = ModelHealthIssue.create_configuration_issue(
            message="Missing HTTP client", severity="high"
        )

        assert isinstance(issue.issue_id, UUID)
        assert issue.severity == "high"
        assert issue.category == "configuration"
        assert issue.message == "Missing HTTP client"
        assert issue.count == 1

    def test_create_configuration_issue_default_severity(self):
        """Test configuration issue with default severity.

        Configuration issues default to 'critical' because they typically
        indicate setup or dependency problems that prevent proper operation.
        """
        issue = ModelHealthIssue.create_configuration_issue(
            message="No protocol client provided"
        )

        assert issue.severity == "critical"
        assert issue.category == "configuration"

    def test_create_validation_issue(self):
        """Test validation issue factory."""
        issue = ModelHealthIssue.create_validation_issue(
            message="Invalid URL format", severity="high"
        )

        assert isinstance(issue.issue_id, UUID)
        assert issue.severity == "high"
        assert issue.category == "validation"
        assert issue.message == "Invalid URL format"
        assert issue.count == 1

    def test_create_validation_issue_default_severity(self):
        """Test validation issue with default severity.

        Validation issues default to 'critical' because they often indicate
        security-related input validation failures (e.g., SSRF prevention).
        """
        issue = ModelHealthIssue.create_validation_issue(
            message="Invalid service URL - SSRF prevention"
        )

        assert issue.severity == "critical"
        assert issue.category == "validation"


class TestModelHealthIssueRecovery:
    """Test recovery configuration."""

    def test_auto_recoverable_issue(self):
        """Test auto-recoverable issue."""
        issue_id = uuid4()
        now = datetime.now(UTC)

        issue = ModelHealthIssue(
            issue_id=issue_id,
            severity="medium",
            category="performance",
            message="test",
            first_detected=now,
            last_seen=now,
            auto_recoverable=True,
            recovery_action="restart service",
        )

        assert issue.auto_recoverable is True
        assert issue.recovery_action == "restart service"

    def test_non_recoverable_issue(self):
        """Test non-recoverable issue."""
        issue_id = uuid4()
        now = datetime.now(UTC)

        issue = ModelHealthIssue(
            issue_id=issue_id,
            severity="critical",
            category="security",
            message="test",
            first_detected=now,
            last_seen=now,
            auto_recoverable=False,
        )

        assert issue.auto_recoverable is False
        assert issue.recovery_action is None
