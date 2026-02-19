# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelInvariantViolationReport."""

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_comparison_type import EnumComparisonType
from omnibase_core.enums.enum_invariant_report_status import EnumInvariantReportStatus
from omnibase_core.enums.enum_invariant_type import EnumInvariantType
from omnibase_core.models.invariant.model_invariant_violation_detail import (
    ModelInvariantViolationDetail,
)
from omnibase_core.models.invariant.model_invariant_violation_report import (
    ModelInvariantViolationReport,
)


def create_violation(
    severity: EnumSeverity,
    name: str = "Test Invariant",
    field_path: str | None = None,
) -> ModelInvariantViolationDetail:
    """Create a test violation detail.

    Args:
        severity: The severity level for the violation.
        name: Human-readable name for the invariant.
        field_path: Optional field path for the violation.

    Returns:
        A configured ModelInvariantViolationDetail instance.
    """
    return ModelInvariantViolationDetail(
        invariant_id=uuid4(),
        invariant_name=name,
        invariant_type=EnumInvariantType.FIELD_VALUE,
        severity=severity,
        message=f"Test {severity.value} violation",
        explanation="Test explanation for debugging",
        comparison_type=EnumComparisonType.EXACT,
        field_path=field_path,
    )


def create_report(
    violations: list[ModelInvariantViolationDetail] | None = None,
    total_invariants: int = 10,
    passed_count: int = 8,
    failed_count: int = 2,
    skipped_count: int = 0,
    status: EnumInvariantReportStatus = EnumInvariantReportStatus.FAILED,
) -> ModelInvariantViolationReport:
    """Create a test report with sensible defaults.

    Args:
        violations: List of violation details. Defaults to empty list.
        total_invariants: Total number of invariants checked.
        passed_count: Number of invariants that passed.
        failed_count: Number of invariants that failed.
        skipped_count: Number of invariants that were skipped.
        status: Overall status of the report.

    Returns:
        A configured ModelInvariantViolationReport instance.
    """
    return ModelInvariantViolationReport(
        evaluation_id=uuid4(),
        invariant_set_id=uuid4(),
        target="test_node",
        evaluated_at=datetime.now(UTC),
        duration_ms=150.5,
        total_invariants=total_invariants,
        passed_count=passed_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        status=status,
        violations=violations or [],
    )


@pytest.mark.unit
class TestReportCreation:
    """Test report creation and validation."""

    def test_creation_with_required_fields(self) -> None:
        """Report creates successfully with required fields."""
        evaluation_id = uuid4()
        invariant_set_id = uuid4()
        evaluated_at = datetime.now(UTC)

        report = ModelInvariantViolationReport(
            evaluation_id=evaluation_id,
            invariant_set_id=invariant_set_id,
            target="node_llm_call",
            evaluated_at=evaluated_at,
            duration_ms=250.0,
            total_invariants=5,
            passed_count=5,
            failed_count=0,
            skipped_count=0,
            status=EnumInvariantReportStatus.PASSED,
        )

        assert report.evaluation_id == evaluation_id
        assert report.invariant_set_id == invariant_set_id
        assert report.target == "node_llm_call"
        assert report.evaluated_at == evaluated_at
        assert report.duration_ms == 250.0
        assert report.total_invariants == 5
        assert report.passed_count == 5
        assert report.failed_count == 0
        assert report.skipped_count == 0
        assert report.status == EnumInvariantReportStatus.PASSED
        assert report.violations == []
        assert report.metadata == {}

    def test_creation_with_optional_fields(self) -> None:
        """Report accepts optional violations and metadata."""
        violation = create_violation(EnumSeverity.CRITICAL)
        metadata = {"run_id": "test-run-123", "environment": "staging"}

        report = ModelInvariantViolationReport(
            evaluation_id=uuid4(),
            invariant_set_id=uuid4(),
            target="node_llm_call",
            evaluated_at=datetime.now(UTC),
            duration_ms=100.0,
            total_invariants=10,
            passed_count=9,
            failed_count=1,
            skipped_count=0,
            status=EnumInvariantReportStatus.FAILED,
            violations=[violation],
            metadata=metadata,
        )

        assert len(report.violations) == 1
        assert report.violations[0].severity == EnumSeverity.CRITICAL
        assert report.metadata == metadata
        assert report.metadata["run_id"] == "test-run-123"

    def test_model_is_frozen(self) -> None:
        """Report is immutable after creation."""
        report = create_report()

        with pytest.raises(ValidationError):
            report.target = "new_target"

    def test_auto_generates_id(self) -> None:
        """Report auto-generates UUID id if not provided."""
        report = create_report()

        assert report.id is not None
        assert isinstance(report.id, UUID)

    def test_duration_ms_must_be_non_negative(self) -> None:
        """Report rejects negative duration_ms."""
        with pytest.raises(ValidationError) as exc_info:
            ModelInvariantViolationReport(
                evaluation_id=uuid4(),
                invariant_set_id=uuid4(),
                target="test_node",
                evaluated_at=datetime.now(UTC),
                duration_ms=-1.0,
                total_invariants=5,
                passed_count=5,
                failed_count=0,
                skipped_count=0,
                status=EnumInvariantReportStatus.PASSED,
            )

        assert "duration_ms" in str(exc_info.value)

    def test_counts_must_be_non_negative(self) -> None:
        """Report rejects negative count values."""
        base_args = {
            "evaluation_id": uuid4(),
            "invariant_set_id": uuid4(),
            "target": "test_node",
            "evaluated_at": datetime.now(UTC),
            "duration_ms": 100.0,
            "status": EnumInvariantReportStatus.PASSED,
        }

        # Test negative total_invariants
        with pytest.raises(ValidationError):
            ModelInvariantViolationReport(
                **base_args,
                total_invariants=-1,
                passed_count=0,
                failed_count=0,
                skipped_count=0,
            )

        # Test negative passed_count
        with pytest.raises(ValidationError):
            ModelInvariantViolationReport(
                **base_args,
                total_invariants=5,
                passed_count=-1,
                failed_count=0,
                skipped_count=0,
            )


@pytest.mark.unit
class TestReportStatistics:
    """Test computed statistics."""

    def test_pass_rate_calculation(self) -> None:
        """pass_rate correctly calculated as passed/total."""
        report = create_report(
            total_invariants=10,
            passed_count=8,
            failed_count=2,
        )

        assert report.pass_rate == pytest.approx(0.8)

    def test_pass_rate_perfect_score(self) -> None:
        """pass_rate returns 1.0 when all invariants pass."""
        report = create_report(
            total_invariants=10,
            passed_count=10,
            failed_count=0,
            status=EnumInvariantReportStatus.PASSED,
        )

        assert report.pass_rate == pytest.approx(1.0)

    def test_pass_rate_zero_passes(self) -> None:
        """pass_rate returns 0.0 when no invariants pass."""
        report = create_report(
            total_invariants=5,
            passed_count=0,
            failed_count=5,
        )

        assert report.pass_rate == pytest.approx(0.0)

    def test_pass_rate_empty_is_one(self) -> None:
        """pass_rate returns 1.0 when total_invariants is 0."""
        report = create_report(
            total_invariants=0,
            passed_count=0,
            failed_count=0,
            status=EnumInvariantReportStatus.PASSED,
        )

        assert report.pass_rate == pytest.approx(1.0)

    def test_severity_counts_match_violations(self) -> None:
        """critical_count, warning_count, info_count match actual violations."""
        violations = [
            create_violation(EnumSeverity.CRITICAL, "Critical 1"),
            create_violation(EnumSeverity.CRITICAL, "Critical 2"),
            create_violation(EnumSeverity.WARNING, "Warning 1"),
            create_violation(EnumSeverity.WARNING, "Warning 2"),
            create_violation(EnumSeverity.WARNING, "Warning 3"),
            create_violation(EnumSeverity.INFO, "Info 1"),
        ]

        report = create_report(
            violations=violations,
            total_invariants=20,
            passed_count=14,
            failed_count=6,
        )

        assert report.critical_count == 2
        assert report.warning_count == 3
        assert report.info_count == 1

    def test_severity_counts_empty_violations(self) -> None:
        """Severity counts return 0 when no violations."""
        report = create_report(violations=[])

        assert report.critical_count == 0
        assert report.warning_count == 0
        assert report.info_count == 0


@pytest.mark.unit
class TestReportQueryMethods:
    """Test filtering and query methods."""

    def test_get_violations_by_severity_exact_match(self) -> None:
        """get_violations_by_severity returns only exact matches."""
        violations = [
            create_violation(EnumSeverity.CRITICAL, "Critical"),
            create_violation(EnumSeverity.WARNING, "Warning 1"),
            create_violation(EnumSeverity.WARNING, "Warning 2"),
            create_violation(EnumSeverity.INFO, "Info"),
        ]

        report = create_report(violations=violations)

        critical_only = report.get_violations_by_severity(EnumSeverity.CRITICAL)
        warning_only = report.get_violations_by_severity(EnumSeverity.WARNING)
        info_only = report.get_violations_by_severity(EnumSeverity.INFO)

        assert len(critical_only) == 1
        assert critical_only[0].invariant_name == "Critical"

        assert len(warning_only) == 2
        assert all(v.severity == EnumSeverity.WARNING for v in warning_only)

        assert len(info_only) == 1
        assert info_only[0].invariant_name == "Info"

    def test_get_violations_at_or_above_info_threshold(self) -> None:
        """INFO threshold returns all violations."""
        violations = [
            create_violation(EnumSeverity.CRITICAL),
            create_violation(EnumSeverity.WARNING),
            create_violation(EnumSeverity.INFO),
        ]

        report = create_report(violations=violations)
        result = report.get_violations_at_or_above(EnumSeverity.INFO)

        assert len(result) == 3

    def test_get_violations_at_or_above_warning_threshold(self) -> None:
        """WARNING threshold returns WARNING + CRITICAL."""
        violations = [
            create_violation(EnumSeverity.CRITICAL, "Critical"),
            create_violation(EnumSeverity.WARNING, "Warning"),
            create_violation(EnumSeverity.INFO, "Info"),
        ]

        report = create_report(violations=violations)
        result = report.get_violations_at_or_above(EnumSeverity.WARNING)

        assert len(result) == 2
        severities = {v.severity for v in result}
        assert EnumSeverity.CRITICAL in severities
        assert EnumSeverity.WARNING in severities
        assert EnumSeverity.INFO not in severities

    def test_get_violations_at_or_above_critical_threshold(self) -> None:
        """CRITICAL threshold returns only CRITICAL."""
        violations = [
            create_violation(EnumSeverity.CRITICAL, "Critical"),
            create_violation(EnumSeverity.WARNING, "Warning"),
            create_violation(EnumSeverity.INFO, "Info"),
        ]

        report = create_report(violations=violations)
        result = report.get_violations_at_or_above(EnumSeverity.CRITICAL)

        assert len(result) == 1
        assert result[0].severity == EnumSeverity.CRITICAL

    def test_has_violations_at_or_above_true(self) -> None:
        """has_violations_at_or_above returns True when violations exist."""
        violations = [
            create_violation(EnumSeverity.WARNING),
            create_violation(EnumSeverity.INFO),
        ]

        report = create_report(violations=violations)

        assert report.has_violations_at_or_above(EnumSeverity.INFO) is True
        assert report.has_violations_at_or_above(EnumSeverity.WARNING) is True

    def test_has_violations_at_or_above_false(self) -> None:
        """has_violations_at_or_above returns False when no violations meet threshold."""
        violations = [
            create_violation(EnumSeverity.INFO),
            create_violation(EnumSeverity.INFO),
        ]

        report = create_report(violations=violations)

        assert report.has_violations_at_or_above(EnumSeverity.WARNING) is False
        assert report.has_violations_at_or_above(EnumSeverity.CRITICAL) is False

    def test_has_violations_at_or_above_empty_list(self) -> None:
        """has_violations_at_or_above returns False with no violations."""
        report = create_report(violations=[])

        assert report.has_violations_at_or_above(EnumSeverity.INFO) is False
        assert report.has_violations_at_or_above(EnumSeverity.WARNING) is False
        assert report.has_violations_at_or_above(EnumSeverity.CRITICAL) is False

    def test_filter_returns_empty_when_none_match(self) -> None:
        """Filters return empty list when no violations match."""
        violations = [
            create_violation(EnumSeverity.INFO),
            create_violation(EnumSeverity.INFO),
        ]

        report = create_report(violations=violations)

        assert report.get_violations_by_severity(EnumSeverity.CRITICAL) == []
        assert report.get_violations_by_severity(EnumSeverity.WARNING) == []
        assert report.get_violations_at_or_above(EnumSeverity.CRITICAL) == []

    def test_query_methods_preserve_violation_order(self) -> None:
        """Query methods return violations in original order."""
        violations = [
            create_violation(EnumSeverity.WARNING, "First"),
            create_violation(EnumSeverity.WARNING, "Second"),
            create_violation(EnumSeverity.WARNING, "Third"),
        ]

        report = create_report(violations=violations)
        result = report.get_violations_by_severity(EnumSeverity.WARNING)

        assert [v.invariant_name for v in result] == ["First", "Second", "Third"]


@pytest.mark.unit
class TestReportOutputFormats:
    """Test output formatting methods."""

    def test_to_summary_dict_json_safe(self) -> None:
        """to_summary_dict returns only JSON-safe primitives."""
        violations = [
            create_violation(EnumSeverity.CRITICAL),
            create_violation(EnumSeverity.WARNING),
        ]

        report = create_report(violations=violations)
        summary = report.to_summary_dict()

        # All values should be str, int, float, or bool
        allowed_types = (str, int, float, bool)
        for key, value in summary.items():
            assert isinstance(value, allowed_types), (
                f"Key '{key}' has non-JSON-safe type: {type(value).__name__}"
            )

        # Verify JSON serializable
        json_str = json.dumps(summary)
        assert json_str is not None

    def test_to_summary_dict_no_enum_objects(self) -> None:
        """to_summary_dict converts enums to string values."""
        report = create_report()
        summary = report.to_summary_dict()

        # Status should be string value, not enum object
        assert isinstance(summary["status"], str)
        assert summary["status"] == "failed"

        # No enum objects should be present
        from enum import Enum

        for key, value in summary.items():
            assert not isinstance(value, Enum), (
                f"Key '{key}' contains enum object: {value}"
            )

    def test_to_summary_dict_contains_expected_keys(self) -> None:
        """to_summary_dict contains all expected keys."""
        report = create_report()
        summary = report.to_summary_dict()

        expected_keys = {
            "id",
            "evaluation_id",
            "invariant_set_id",
            "target",
            "status",
            "total_invariants",
            "passed_count",
            "failed_count",
            "skipped_count",
            "pass_rate",
            "critical_count",
            "warning_count",
            "info_count",
            "duration_ms",
            "evaluated_at",
        }

        assert set(summary.keys()) == expected_keys

    def test_to_summary_dict_pass_rate_rounded(self) -> None:
        """to_summary_dict rounds pass_rate to 4 decimal places."""
        report = create_report(
            total_invariants=3,
            passed_count=1,
            failed_count=2,
        )
        summary = report.to_summary_dict()

        # 1/3 = 0.333333... should be rounded to 0.3333
        assert summary["pass_rate"] == pytest.approx(0.3333, abs=0.0001)

    def test_to_summary_dict_evaluated_at_iso_format(self) -> None:
        """to_summary_dict formats evaluated_at as ISO-8601 string."""
        report = create_report()
        summary = report.to_summary_dict()

        # Should be parseable as ISO format
        evaluated_at_str = summary["evaluated_at"]
        assert isinstance(evaluated_at_str, str)
        # ISO format includes T separator
        datetime.fromisoformat(evaluated_at_str)  # Should not raise

    def test_to_markdown_deterministic(self) -> None:
        """to_markdown produces consistent output for same input."""
        violations = [
            create_violation(EnumSeverity.CRITICAL, "Critical Check"),
        ]
        evaluated_at = datetime(2025, 1, 15, 12, 30, 45, tzinfo=UTC)
        # Use fixed UUIDs for deterministic test
        fixed_id = UUID("12345678-1234-5678-1234-567812345678")
        fixed_eval_id = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        fixed_set_id = UUID("11111111-2222-3333-4444-555555555555")

        report = ModelInvariantViolationReport(
            id=fixed_id,
            evaluation_id=fixed_eval_id,
            invariant_set_id=fixed_set_id,
            target="test_node",
            evaluated_at=evaluated_at,
            duration_ms=150.0,
            total_invariants=10,
            passed_count=9,
            failed_count=1,
            skipped_count=0,
            status=EnumInvariantReportStatus.FAILED,
            violations=violations,
        )

        markdown1 = report.to_markdown()
        markdown2 = report.to_markdown()

        assert markdown1 == markdown2

    def test_to_markdown_includes_all_sections(self) -> None:
        """to_markdown includes summary, critical, warnings, info sections."""
        violations = [
            create_violation(EnumSeverity.CRITICAL, "Critical Issue", "field.critical"),
            create_violation(EnumSeverity.WARNING, "Warning Issue", "field.warning"),
            create_violation(EnumSeverity.INFO, "Info Issue"),
        ]

        report = create_report(violations=violations, total_invariants=10)
        markdown = report.to_markdown()

        # Check for main sections
        assert "# Invariant Evaluation Report" in markdown
        assert "## Summary" in markdown
        assert "## Critical Failures" in markdown
        assert "## Warnings" in markdown
        assert "## Info" in markdown

        # Check for content
        assert "Critical Issue" in markdown
        assert "Warning Issue" in markdown
        assert "Info Issue" in markdown
        assert "test_node" in markdown

    def test_to_markdown_includes_table(self) -> None:
        """to_markdown includes summary table with metrics."""
        report = create_report(
            total_invariants=10,
            passed_count=8,
            failed_count=1,
            skipped_count=1,
        )
        markdown = report.to_markdown()

        assert "| Metric | Value |" in markdown
        assert "| Total Invariants | 10 |" in markdown
        assert "| Passed | 8 |" in markdown
        assert "| Failed | 1 |" in markdown
        assert "| Skipped | 1 |" in markdown
        assert "Pass Rate" in markdown

    def test_to_markdown_empty_violations(self) -> None:
        """to_markdown handles empty violations gracefully."""
        report = create_report(
            violations=[],
            total_invariants=5,
            passed_count=5,
            failed_count=0,
            status=EnumInvariantReportStatus.PASSED,
        )
        markdown = report.to_markdown()

        assert "# Invariant Evaluation Report" in markdown
        assert "## Summary" in markdown
        assert "No violations detected" in markdown
        # Should not have severity-specific sections
        assert "## Critical Failures" not in markdown
        assert "## Warnings" not in markdown
        assert "## Info" not in markdown

    def test_to_markdown_includes_field_path(self) -> None:
        """to_markdown includes field path when present in violation."""
        violation = create_violation(
            EnumSeverity.CRITICAL,
            "Field Check",
            field_path="response.data.value",
        )
        report = create_report(violations=[violation])
        markdown = report.to_markdown()

        assert "response.data.value" in markdown
        assert "**Field**:" in markdown

    def test_to_markdown_status_uppercase(self) -> None:
        """to_markdown shows status in uppercase."""
        report = create_report(status=EnumInvariantReportStatus.FAILED)
        markdown = report.to_markdown()

        assert "**Status**: FAILED" in markdown


@pytest.mark.unit
class TestReportSerialization:
    """Test serialization roundtrip."""

    def test_serialization_roundtrip(self) -> None:
        """JSON serialization and deserialization preserves all data.

        Note: Computed fields (pass_rate, critical_count, warning_count, info_count)
        are excluded from serialization to allow roundtrip with extra="forbid".
        These fields are recomputed on deserialization.
        """
        violations = [
            create_violation(EnumSeverity.CRITICAL, "Critical"),
            create_violation(EnumSeverity.WARNING, "Warning"),
            create_violation(EnumSeverity.INFO, "Info"),
        ]

        original = create_report(
            violations=violations,
            total_invariants=15,
            passed_count=12,
            failed_count=3,
        )

        # Serialize to dict excluding computed fields, then to JSON
        # Computed fields must be excluded for roundtrip with extra="forbid"
        data = original.model_dump(
            exclude={"pass_rate", "critical_count", "warning_count", "info_count"}
        )
        json_str = json.dumps(data, default=str)

        # Deserialize back
        restored = ModelInvariantViolationReport.model_validate_json(json_str)

        # Verify all stored fields match
        assert restored.id == original.id
        assert restored.evaluation_id == original.evaluation_id
        assert restored.invariant_set_id == original.invariant_set_id
        assert restored.target == original.target
        assert restored.evaluated_at == original.evaluated_at
        assert restored.duration_ms == original.duration_ms
        assert restored.total_invariants == original.total_invariants
        assert restored.passed_count == original.passed_count
        assert restored.failed_count == original.failed_count
        assert restored.skipped_count == original.skipped_count
        assert restored.status == original.status
        assert len(restored.violations) == len(original.violations)

        # Verify computed fields are recomputed correctly
        assert restored.pass_rate == original.pass_rate
        assert restored.critical_count == original.critical_count
        assert restored.warning_count == original.warning_count
        assert restored.info_count == original.info_count

    def test_model_dump_excludes_none_by_default(self) -> None:
        """model_dump with exclude_none removes None values."""
        report = create_report()
        dumped = report.model_dump(exclude_none=True)

        # Check that None values are excluded
        for key, value in dumped.items():
            if key != "violations":
                assert value is not None, f"Key '{key}' has None value"

    def test_serialization_preserves_violation_details(self) -> None:
        """Serialization preserves all violation detail fields."""
        violation = ModelInvariantViolationDetail(
            invariant_id=uuid4(),
            invariant_name="Test Check",
            invariant_type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            field_path="response.latency",
            actual_value=7500,
            expected_value=5000,
            message="Latency exceeded",
            explanation="Response took too long",
            comparison_type=EnumComparisonType.RANGE,
            operator="<=",
            suggestion="Consider caching",
            related_fields=["response.cached", "response.ttl"],
        )

        original = create_report(violations=[violation])

        # Serialize excluding computed fields for roundtrip
        data = original.model_dump(
            exclude={"pass_rate", "critical_count", "warning_count", "info_count"}
        )
        json_str = json.dumps(data, default=str)
        restored = ModelInvariantViolationReport.model_validate_json(json_str)

        restored_violation = restored.violations[0]
        assert restored_violation.invariant_name == "Test Check"
        assert restored_violation.field_path == "response.latency"
        assert restored_violation.actual_value == 7500
        assert restored_violation.expected_value == 5000
        assert restored_violation.operator == "<="
        assert restored_violation.suggestion == "Consider caching"
        assert restored_violation.related_fields == ["response.cached", "response.ttl"]

    def test_computed_fields_included_in_model_dump(self) -> None:
        """Computed fields are included when using model_dump without exclusions."""
        violations = [
            create_violation(EnumSeverity.CRITICAL),
            create_violation(EnumSeverity.WARNING),
        ]
        report = create_report(violations=violations)

        dumped = report.model_dump()

        # Computed fields should be present
        assert "pass_rate" in dumped
        assert "critical_count" in dumped
        assert "warning_count" in dumped
        assert "info_count" in dumped

        # Values should match computed properties
        assert dumped["pass_rate"] == report.pass_rate
        assert dumped["critical_count"] == 1
        assert dumped["warning_count"] == 1
        assert dumped["info_count"] == 0


@pytest.mark.unit
class TestReportStatusValues:
    """Test all report status values work correctly."""

    @pytest.mark.parametrize("status", list(EnumInvariantReportStatus))
    def test_all_status_values_accepted(
        self, status: EnumInvariantReportStatus
    ) -> None:
        """All report status values should be valid."""
        report = create_report(status=status)
        assert report.status == status

    def test_status_passed_implies_no_failures(self) -> None:
        """PASSED status typically implies no violations (contract-driven check)."""
        # Note: This is a documentation test - the model doesn't enforce this
        # The calling code (contract) determines what constitutes "passed"
        report = create_report(
            violations=[],
            total_invariants=10,
            passed_count=10,
            failed_count=0,
            status=EnumInvariantReportStatus.PASSED,
        )
        assert report.status == EnumInvariantReportStatus.PASSED
        assert not report.has_violations_at_or_above(EnumSeverity.INFO)


@pytest.mark.unit
class TestNegativeValueValidation:
    """Test that negative values are properly rejected for count fields."""

    def test_negative_total_invariants_rejected(self) -> None:
        """Report rejects negative total_invariants."""
        with pytest.raises(ValidationError):
            ModelInvariantViolationReport(
                evaluation_id=uuid4(),
                invariant_set_id=uuid4(),
                target="test_node",
                evaluated_at=datetime.now(UTC),
                duration_ms=100.0,
                total_invariants=-1,
                passed_count=0,
                failed_count=0,
                skipped_count=0,
                status=EnumInvariantReportStatus.PASSED,
            )

    def test_negative_passed_count_rejected(self) -> None:
        """Report rejects negative passed_count."""
        with pytest.raises(ValidationError):
            ModelInvariantViolationReport(
                evaluation_id=uuid4(),
                invariant_set_id=uuid4(),
                target="test_node",
                evaluated_at=datetime.now(UTC),
                duration_ms=100.0,
                total_invariants=10,
                passed_count=-1,
                failed_count=5,
                skipped_count=0,
                status=EnumInvariantReportStatus.FAILED,
            )

    def test_negative_failed_count_rejected(self) -> None:
        """Report rejects negative failed_count."""
        with pytest.raises(ValidationError):
            ModelInvariantViolationReport(
                evaluation_id=uuid4(),
                invariant_set_id=uuid4(),
                target="test_node",
                evaluated_at=datetime.now(UTC),
                duration_ms=100.0,
                total_invariants=10,
                passed_count=10,
                failed_count=-1,
                skipped_count=0,
                status=EnumInvariantReportStatus.PASSED,
            )

    def test_negative_skipped_count_rejected(self) -> None:
        """Report rejects negative skipped_count."""
        with pytest.raises(ValidationError):
            ModelInvariantViolationReport(
                evaluation_id=uuid4(),
                invariant_set_id=uuid4(),
                target="test_node",
                evaluated_at=datetime.now(UTC),
                duration_ms=100.0,
                total_invariants=10,
                passed_count=8,
                failed_count=2,
                skipped_count=-1,
                status=EnumInvariantReportStatus.FAILED,
            )

    def test_inconsistent_counts_rejected(self) -> None:
        """Report rejects counts that don't sum to total_invariants.

        This test validates the data consistency constraint:
        passed_count + failed_count + skipped_count == total_invariants
        """
        with pytest.raises(ValidationError, match="Count mismatch"):
            ModelInvariantViolationReport(
                evaluation_id=uuid4(),
                invariant_set_id=uuid4(),
                target="test_node",
                evaluated_at=datetime.now(UTC),
                duration_ms=100.0,
                total_invariants=10,
                passed_count=5,
                failed_count=2,  # 5+2+0=7 != 10
                skipped_count=0,
                status=EnumInvariantReportStatus.PASSED,
            )


@pytest.mark.unit
class TestReportMetadata:
    """Test metadata handling."""

    def test_metadata_accepts_arbitrary_string_pairs(self) -> None:
        """Metadata accepts arbitrary string key-value pairs."""
        metadata = {
            "environment": "production",
            "region": "us-east-1",
            "commit_sha": "abc123def456",
            "pipeline_id": "pipeline-789",
        }

        report = ModelInvariantViolationReport(
            evaluation_id=uuid4(),
            invariant_set_id=uuid4(),
            target="test_node",
            evaluated_at=datetime.now(UTC),
            duration_ms=100.0,
            total_invariants=5,
            passed_count=5,
            failed_count=0,
            skipped_count=0,
            status=EnumInvariantReportStatus.PASSED,
            metadata=metadata,
        )

        assert report.metadata == metadata
        assert report.metadata["environment"] == "production"

    def test_metadata_defaults_to_empty_dict(self) -> None:
        """Metadata defaults to empty dict when not provided."""
        report = create_report()
        assert report.metadata == {}
        assert isinstance(report.metadata, dict)

    def test_metadata_serialization_roundtrip(self) -> None:
        """Metadata survives JSON serialization roundtrip."""
        metadata = {"key1": "value1", "key2": "value2"}
        original = ModelInvariantViolationReport(
            evaluation_id=uuid4(),
            invariant_set_id=uuid4(),
            target="test_node",
            evaluated_at=datetime.now(UTC),
            duration_ms=100.0,
            total_invariants=5,
            passed_count=5,
            failed_count=0,
            skipped_count=0,
            status=EnumInvariantReportStatus.PASSED,
            metadata=metadata,
        )

        # Exclude computed fields for roundtrip compatibility with extra="forbid"
        data = original.model_dump(
            exclude={"pass_rate", "critical_count", "warning_count", "info_count"}
        )
        json_str = json.dumps(data, default=str)
        restored = ModelInvariantViolationReport.model_validate_json(json_str)

        assert restored.metadata == metadata
