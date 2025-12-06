"""
Comprehensive tests for ModelUnifiedSummary.

Tests cover:
- Basic instantiation with required fields
- Field validation with non-negative constraints
- Optional notes and details fields
- Field validation and type safety
- Edge cases and boundary conditions
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.results.model_unified_summary import ModelUnifiedSummary
from omnibase_core.models.results.model_unified_summary_details import (
    ModelUnifiedSummaryDetails,
)


class TestModelUnifiedSummaryBasicInstantiation:
    """Test basic instantiation with required fields."""

    def test_minimal_instantiation_with_required_fields(self):
        """Test creating summary with required count fields."""
        summary = ModelUnifiedSummary(
            total=10,
            passed=8,
            failed=2,
            skipped=0,
            fixed=0,
            warnings=0,
        )

        assert summary.total == 10
        assert summary.passed == 8
        assert summary.failed == 2
        assert summary.skipped == 0
        assert summary.fixed == 0
        assert summary.warnings == 0

    def test_instantiation_with_all_fields(self):
        """Test creating summary with all fields populated."""
        details = ModelUnifiedSummaryDetails(
            key="detail_key", value=ModelSchemaValue.from_value("detail_value")
        )
        notes = ["Note 1", "Note 2"]

        summary = ModelUnifiedSummary(
            total=100,
            passed=80,
            failed=15,
            skipped=5,
            fixed=10,
            warnings=3,
            notes=notes,
            details=details,
        )

        assert summary.total == 100
        assert summary.passed == 80
        assert summary.failed == 15
        assert summary.skipped == 5
        assert summary.fixed == 10
        assert summary.warnings == 3
        assert len(summary.notes) == 2
        assert summary.details.key == "detail_key"


class TestModelUnifiedSummaryFieldValidation:
    """Test field validation and constraints."""

    def test_required_fields_validation(self):
        """Test that all count fields are required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelUnifiedSummary()

        errors = exc_info.value.errors()
        error_fields = {error["loc"][0] for error in errors}

        assert "total" in error_fields
        assert "passed" in error_fields
        assert "failed" in error_fields
        assert "skipped" in error_fields
        assert "fixed" in error_fields
        assert "warnings" in error_fields

    def test_fields_must_be_non_negative(self):
        """Test that count fields must be >= 0."""
        # Negative total
        with pytest.raises(ValidationError):
            ModelUnifiedSummary(
                total=-1,
                passed=0,
                failed=0,
                skipped=0,
                fixed=0,
                warnings=0,
            )

        # Negative passed
        with pytest.raises(ValidationError):
            ModelUnifiedSummary(
                total=10,
                passed=-1,
                failed=0,
                skipped=0,
                fixed=0,
                warnings=0,
            )

        # Negative failed
        with pytest.raises(ValidationError):
            ModelUnifiedSummary(
                total=10,
                passed=0,
                failed=-1,
                skipped=0,
                fixed=0,
                warnings=0,
            )

    def test_zero_values_accepted(self):
        """Test that zero values are valid."""
        summary = ModelUnifiedSummary(
            total=0,
            passed=0,
            failed=0,
            skipped=0,
            fixed=0,
            warnings=0,
        )

        assert summary.total == 0
        assert summary.passed == 0
        assert summary.failed == 0


class TestModelUnifiedSummaryCountFields:
    """Test individual count fields."""

    def test_total_field(self):
        """Test total field."""
        summary = ModelUnifiedSummary(
            total=100,
            passed=80,
            failed=15,
            skipped=5,
            fixed=10,
            warnings=3,
        )

        assert summary.total == 100
        assert isinstance(summary.total, int)

    def test_passed_field(self):
        """Test passed field."""
        summary = ModelUnifiedSummary(
            total=10,
            passed=8,
            failed=2,
            skipped=0,
            fixed=0,
            warnings=0,
        )

        assert summary.passed == 8

    def test_failed_field(self):
        """Test failed field."""
        summary = ModelUnifiedSummary(
            total=10,
            passed=5,
            failed=5,
            skipped=0,
            fixed=0,
            warnings=0,
        )

        assert summary.failed == 5

    def test_skipped_field(self):
        """Test skipped field."""
        summary = ModelUnifiedSummary(
            total=10,
            passed=5,
            failed=3,
            skipped=2,
            fixed=0,
            warnings=0,
        )

        assert summary.skipped == 2

    def test_fixed_field(self):
        """Test fixed field."""
        summary = ModelUnifiedSummary(
            total=10,
            passed=8,
            failed=2,
            skipped=0,
            fixed=5,
            warnings=0,
        )

        assert summary.fixed == 5

    def test_warnings_field(self):
        """Test warnings field."""
        summary = ModelUnifiedSummary(
            total=10,
            passed=7,
            failed=0,
            skipped=0,
            fixed=0,
            warnings=3,
        )

        assert summary.warnings == 3


class TestModelUnifiedSummaryNotesField:
    """Test notes field handling."""

    def test_notes_field_with_list(self):
        """Test notes field with list of strings."""
        notes = ["First note", "Second note", "Third note"]
        summary = ModelUnifiedSummary(
            total=10,
            passed=10,
            failed=0,
            skipped=0,
            fixed=0,
            warnings=0,
            notes=notes,
        )

        assert len(summary.notes) == 3
        assert summary.notes[0] == "First note"
        assert "Second note" in summary.notes

    def test_notes_field_optional(self):
        """Test that notes field is optional."""
        summary = ModelUnifiedSummary(
            total=10,
            passed=10,
            failed=0,
            skipped=0,
            fixed=0,
            warnings=0,
        )

        assert summary.notes is None

    def test_notes_field_with_empty_list(self):
        """Test notes field with empty list."""
        summary = ModelUnifiedSummary(
            total=10,
            passed=10,
            failed=0,
            skipped=0,
            fixed=0,
            warnings=0,
            notes=[],
        )

        assert summary.notes == []


class TestModelUnifiedSummaryDetailsField:
    """Test details field integration."""

    def test_details_field_with_summary_details(self):
        """Test details field with ModelUnifiedSummaryDetails instance."""
        details = ModelUnifiedSummaryDetails(
            key="coverage", value=ModelSchemaValue.from_value("85.5")
        )
        summary = ModelUnifiedSummary(
            total=100,
            passed=85,
            failed=15,
            skipped=0,
            fixed=10,
            warnings=5,
            details=details,
        )

        assert summary.details.key == "coverage"
        assert summary.details.value.string_value == "85.5"

    def test_details_field_optional(self):
        """Test that details field is optional."""
        summary = ModelUnifiedSummary(
            total=10,
            passed=10,
            failed=0,
            skipped=0,
            fixed=0,
            warnings=0,
        )

        assert summary.details is None


class TestModelUnifiedSummarySerialization:
    """Test model serialization and deserialization."""

    def test_model_dump_basic(self):
        """Test model_dump() produces correct dictionary."""
        summary = ModelUnifiedSummary(
            total=100,
            passed=80,
            failed=15,
            skipped=5,
            fixed=10,
            warnings=3,
        )

        dumped = summary.model_dump()

        assert dumped["total"] == 100
        assert dumped["passed"] == 80
        assert dumped["failed"] == 15
        assert dumped["skipped"] == 5
        assert dumped["fixed"] == 10
        assert dumped["warnings"] == 3

    def test_model_dump_exclude_none(self):
        """Test model_dump(exclude_none=True) removes None fields."""
        summary = ModelUnifiedSummary(
            total=10,
            passed=10,
            failed=0,
            skipped=0,
            fixed=0,
            warnings=0,
        )

        dumped = summary.model_dump(exclude_none=True)

        assert "total" in dumped
        assert "passed" in dumped
        assert "notes" not in dumped  # None
        assert "details" not in dumped  # None

    def test_model_dump_json_roundtrip(self):
        """Test JSON serialization roundtrip."""
        original = ModelUnifiedSummary(
            total=100,
            passed=80,
            failed=15,
            skipped=5,
            fixed=10,
            warnings=3,
            notes=["Test note"],
        )

        json_str = original.model_dump_json()
        restored = ModelUnifiedSummary.model_validate_json(json_str)

        assert restored.total == original.total
        assert restored.passed == original.passed
        assert restored.failed == original.failed
        assert restored.skipped == original.skipped
        assert restored.fixed == original.fixed
        assert restored.warnings == original.warnings
        assert restored.notes == original.notes


class TestModelUnifiedSummaryComplexScenarios:
    """Test complex usage scenarios."""

    def test_perfect_pass_scenario(self):
        """Test summary for 100% pass rate."""
        summary = ModelUnifiedSummary(
            total=100,
            passed=100,
            failed=0,
            skipped=0,
            fixed=0,
            warnings=0,
        )

        assert summary.total == 100
        assert summary.passed == 100
        assert summary.failed == 0
        assert summary.passed == summary.total

    def test_mixed_results_scenario(self):
        """Test summary with mixed results."""
        summary = ModelUnifiedSummary(
            total=200,
            passed=150,
            failed=30,
            skipped=20,
            fixed=25,
            warnings=10,
            notes=["Some tests were flaky", "Fixed 25 issues automatically"],
        )

        assert summary.total == 200
        assert summary.passed + summary.failed + summary.skipped == 200
        assert summary.fixed > 0
        assert summary.warnings > 0

    def test_all_failed_scenario(self):
        """Test summary with all failures."""
        summary = ModelUnifiedSummary(
            total=50,
            passed=0,
            failed=50,
            skipped=0,
            fixed=0,
            warnings=25,
            notes=["All tests failed"],
        )

        assert summary.failed == summary.total
        assert summary.passed == 0

    def test_large_scale_summary(self):
        """Test summary with large numbers."""
        summary = ModelUnifiedSummary(
            total=1000000,
            passed=980000,
            failed=15000,
            skipped=5000,
            fixed=10000,
            warnings=500,
        )

        assert summary.total == 1000000
        assert summary.passed > 900000


class TestModelUnifiedSummaryEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_all_zeros(self):
        """Test summary with all zero values."""
        summary = ModelUnifiedSummary(
            total=0,
            passed=0,
            failed=0,
            skipped=0,
            fixed=0,
            warnings=0,
        )

        assert summary.total == 0
        assert summary.passed == 0
        assert summary.failed == 0

    def test_fixed_greater_than_failed(self):
        """Test that fixed can be greater than failed (fixed across runs)."""
        summary = ModelUnifiedSummary(
            total=100,
            passed=90,
            failed=10,
            skipped=0,
            fixed=20,
            warnings=0,
        )

        assert summary.fixed > summary.failed

    def test_warnings_with_no_failures(self):
        """Test warnings present even with no failures."""
        summary = ModelUnifiedSummary(
            total=100,
            passed=100,
            failed=0,
            skipped=0,
            fixed=0,
            warnings=15,
        )

        assert summary.failed == 0
        assert summary.warnings > 0

    def test_single_note(self):
        """Test notes field with single note."""
        summary = ModelUnifiedSummary(
            total=10,
            passed=10,
            failed=0,
            skipped=0,
            fixed=0,
            warnings=0,
            notes=["Single note"],
        )

        assert len(summary.notes) == 1
        assert summary.notes[0] == "Single note"


class TestModelUnifiedSummaryCalculations:
    """Test summary calculations and relationships."""

    def test_passed_plus_failed_plus_skipped_equals_total(self):
        """Test that passed + failed + skipped can equal total."""
        summary = ModelUnifiedSummary(
            total=100,
            passed=70,
            failed=20,
            skipped=10,
            fixed=0,
            warnings=0,
        )

        assert summary.passed + summary.failed + summary.skipped == summary.total

    def test_pass_rate_calculation(self):
        """Test calculating pass rate from summary."""
        summary = ModelUnifiedSummary(
            total=100,
            passed=80,
            failed=20,
            skipped=0,
            fixed=0,
            warnings=0,
        )

        if summary.total > 0:
            pass_rate = (summary.passed / summary.total) * 100
            assert pass_rate == 80.0

    def test_failure_rate_calculation(self):
        """Test calculating failure rate from summary."""
        summary = ModelUnifiedSummary(
            total=100,
            passed=75,
            failed=25,
            skipped=0,
            fixed=0,
            warnings=0,
        )

        if summary.total > 0:
            failure_rate = (summary.failed / summary.total) * 100
            assert failure_rate == 25.0


class TestModelUnifiedSummaryTypeSafety:
    """Test type safety - ZERO TOLERANCE for Any types."""

    def test_no_any_types_in_annotations(self):
        """Test that model fields don't use Any type."""
        from typing import get_type_hints

        hints = get_type_hints(ModelUnifiedSummary)

        # Check that no field uses Any type
        for field_name, field_type in hints.items():
            type_str = str(field_type)
            assert "typing.Any" not in type_str or "None" in type_str, (
                f"Field {field_name} uses Any type: {type_str}"
            )

    def test_count_fields_are_integers(self):
        """Test that count fields are properly typed as int."""
        from typing import get_type_hints

        hints = get_type_hints(ModelUnifiedSummary)

        assert hints["total"] == int
        assert hints["passed"] == int
        assert hints["failed"] == int
        assert hints["skipped"] == int
        assert hints["fixed"] == int
        assert hints["warnings"] == int

    def test_notes_field_properly_typed(self):
        """Test that notes field is properly typed as list[str] | None."""
        from typing import get_type_hints

        hints = get_type_hints(ModelUnifiedSummary)
        notes_type = hints.get("notes")

        assert notes_type is not None
        type_str = str(notes_type)
        assert "list" in type_str
        assert "str" in type_str
