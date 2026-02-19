# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Test suite for ModelValidationContainer - validation error aggregator and reporting.

This test suite focuses on validator branches and conditional logic to maximize branch coverage.
"""

from __future__ import annotations

import pytest

from omnibase_core.models.validation.model_validation_container import (
    ModelValidationContainer,
)
from omnibase_core.models.validation.model_validation_error import ModelValidationError
from omnibase_core.models.validation.model_validation_value import ModelValidationValue


@pytest.mark.unit
class TestModelValidationContainerInstantiation:
    """Test basic model instantiation."""

    def test_default_initialization(self):
        """Test default initialization creates empty lists."""
        container = ModelValidationContainer()
        assert container.errors == []
        assert container.warnings == []

    def test_initialization_with_errors(self):
        """Test initialization with errors."""
        error = ModelValidationError.create_error(
            message="Test error", field_name="test_field"
        )
        container = ModelValidationContainer(errors=[error])
        assert len(container.errors) == 1
        assert container.errors[0].message == "Test error"

    def test_initialization_with_warnings(self):
        """Test initialization with warnings."""
        container = ModelValidationContainer(warnings=["Warning 1", "Warning 2"])
        assert len(container.warnings) == 2


@pytest.mark.unit
class TestModelValidationContainerAddErrorBranches:
    """Test add_error and add_error_with_raw_details branches."""

    def test_add_error_without_details(self):
        """Test add_error without details (details=None branch)."""
        container = ModelValidationContainer()
        container.add_error("Test error", field="test_field")

        assert len(container.errors) == 1
        assert container.errors[0].message == "Test error"
        assert container.errors[0].field_display_name == "test_field"

    def test_add_error_with_details(self):
        """Test add_error with details (details not None branch)."""
        container = ModelValidationContainer()
        details = {
            "value": ModelValidationValue.from_string("test"),
            "expected": ModelValidationValue.from_string("expected_value"),
        }
        container.add_error("Test error", field="test_field", details=details)

        assert len(container.errors) == 1
        assert container.errors[0].details == details

    def test_add_error_with_raw_details_none(self):
        """Test add_error_with_raw_details with None raw_details (branch: raw_details is None)."""
        container = ModelValidationContainer()
        container.add_error_with_raw_details(
            message="Test error", field="test_field", raw_details=None
        )

        assert len(container.errors) == 1
        assert container.errors[0].message == "Test error"

    def test_add_error_with_raw_details_provided(self):
        """Test add_error_with_raw_details with provided raw_details (branch: raw_details not None)."""
        container = ModelValidationContainer()
        raw_details = {"value": "test_string", "count": 42, "flag": True, "empty": None}
        container.add_error_with_raw_details(
            message="Test error", field="test_field", raw_details=raw_details
        )

        assert len(container.errors) == 1
        error = container.errors[0]
        assert error.details is not None
        assert len(error.details) == 4
        # Verify conversion to ModelValidationValue
        assert isinstance(error.details["value"], ModelValidationValue)
        assert error.details["value"].raw_value == "test_string"

    def test_add_error_with_all_parameters(self):
        """Test add_error with all parameters."""
        container = ModelValidationContainer()
        container.add_error(
            message="Full error", field="field_name", error_code="ERROR_001"
        )

        assert len(container.errors) == 1
        error = container.errors[0]
        assert error.message == "Full error"
        assert error.field_display_name == "field_name"
        assert error.error_code == "ERROR_001"


@pytest.mark.unit
class TestModelValidationContainerAddCriticalErrorBranches:
    """Test add_critical_error branches."""

    def test_add_critical_error_without_details(self):
        """Test add_critical_error without details (details=None branch)."""
        container = ModelValidationContainer()
        container.add_critical_error("Critical error", field="field")

        assert len(container.errors) == 1
        assert container.errors[0].is_critical() is True

    def test_add_critical_error_with_details(self):
        """Test add_critical_error with details (details not None branch)."""
        container = ModelValidationContainer()
        details = {"key": ModelValidationValue.from_string("value")}
        container.add_critical_error("Critical error", details=details)

        assert len(container.errors) == 1
        assert container.errors[0].is_critical() is True
        assert container.errors[0].details == details

    def test_add_critical_error_with_raw_details_none(self):
        """Test add_critical_error_with_raw_details with None (branch: raw_details is None)."""
        container = ModelValidationContainer()
        container.add_critical_error_with_raw_details(
            message="Critical", raw_details=None
        )

        assert len(container.errors) == 1
        assert container.errors[0].is_critical() is True

    def test_add_critical_error_with_raw_details_provided(self):
        """Test add_critical_error_with_raw_details with data (branch: raw_details not None)."""
        container = ModelValidationContainer()
        container.add_critical_error_with_raw_details(
            message="Critical", raw_details={"reason": "security_violation"}
        )

        assert len(container.errors) == 1
        assert container.errors[0].is_critical() is True
        assert container.errors[0].details is not None


@pytest.mark.unit
class TestModelValidationContainerAddWarningBranches:
    """Test add_warning deduplication branches."""

    def test_add_warning_new_message(self):
        """Test add_warning with new message (branch: message not in warnings)."""
        container = ModelValidationContainer()
        container.add_warning("Warning 1")

        assert len(container.warnings) == 1
        assert container.warnings[0] == "Warning 1"

    def test_add_warning_duplicate_message(self):
        """Test add_warning with duplicate message (branch: message in warnings)."""
        container = ModelValidationContainer()
        container.add_warning("Warning 1")
        container.add_warning("Warning 1")  # Duplicate

        assert len(container.warnings) == 1  # Should not add duplicate

    def test_add_warning_multiple_different(self):
        """Test add_warning with multiple different messages."""
        container = ModelValidationContainer()
        container.add_warning("Warning 1")
        container.add_warning("Warning 2")
        container.add_warning("Warning 3")

        assert len(container.warnings) == 3


@pytest.mark.unit
class TestModelValidationContainerQueryMethods:
    """Test query methods (has_errors, has_critical_errors, etc.)."""

    def test_has_errors_true(self):
        """Test has_errors returns True when errors exist."""
        container = ModelValidationContainer()
        container.add_error("Error")
        assert container.has_errors() is True

    def test_has_errors_false(self):
        """Test has_errors returns False when no errors."""
        container = ModelValidationContainer()
        assert container.has_errors() is False

    def test_has_critical_errors_true(self):
        """Test has_critical_errors returns True when critical errors exist."""
        container = ModelValidationContainer()
        container.add_critical_error("Critical")
        assert container.has_critical_errors() is True

    def test_has_critical_errors_false_with_normal_errors(self):
        """Test has_critical_errors returns False when only normal errors exist."""
        container = ModelValidationContainer()
        container.add_error("Normal error")
        assert container.has_critical_errors() is False

    def test_has_critical_errors_false_empty(self):
        """Test has_critical_errors returns False when no errors."""
        container = ModelValidationContainer()
        assert container.has_critical_errors() is False

    def test_has_warnings_true(self):
        """Test has_warnings returns True when warnings exist."""
        container = ModelValidationContainer()
        container.add_warning("Warning")
        assert container.has_warnings() is True

    def test_has_warnings_false(self):
        """Test has_warnings returns False when no warnings."""
        container = ModelValidationContainer()
        assert container.has_warnings() is False


@pytest.mark.unit
class TestModelValidationContainerGetErrorSummaryBranches:
    """Test get_error_summary conditional branches."""

    def test_get_error_summary_no_issues(self):
        """Test summary with no errors or warnings (branch: not has_errors() and not has_warnings())."""
        container = ModelValidationContainer()
        summary = container.get_error_summary()
        assert summary == "No validation issues"

    def test_get_error_summary_single_error_only(self):
        """Test summary with single error (branch: count == 1, singular form)."""
        container = ModelValidationContainer()
        container.add_error("Single error")
        summary = container.get_error_summary()
        assert summary == "1 error"

    def test_get_error_summary_multiple_errors_only(self):
        """Test summary with multiple errors (branch: count != 1, plural form)."""
        container = ModelValidationContainer()
        container.add_error("Error 1")
        container.add_error("Error 2")
        summary = container.get_error_summary()
        assert summary == "2 errors"

    def test_get_error_summary_with_critical_errors(self):
        """Test summary with critical errors (branch: has_critical_errors())."""
        container = ModelValidationContainer()
        container.add_error("Normal error")
        container.add_critical_error("Critical error 1")
        container.add_critical_error("Critical error 2")
        summary = container.get_error_summary()
        assert "3 errors" in summary
        assert "(2 critical)" in summary

    def test_get_error_summary_single_warning_only(self):
        """Test summary with single warning (branch: count == 1, singular form)."""
        container = ModelValidationContainer()
        container.add_warning("Single warning")
        summary = container.get_error_summary()
        assert summary == "1 warning"

    def test_get_error_summary_multiple_warnings_only(self):
        """Test summary with multiple warnings (branch: count != 1, plural form)."""
        container = ModelValidationContainer()
        container.add_warning("Warning 1")
        container.add_warning("Warning 2")
        container.add_warning("Warning 3")
        summary = container.get_error_summary()
        assert summary == "3 warnings"

    def test_get_error_summary_errors_and_warnings(self):
        """Test summary with both errors and warnings."""
        container = ModelValidationContainer()
        container.add_error("Error 1")
        container.add_error("Error 2")
        container.add_warning("Warning 1")
        summary = container.get_error_summary()
        assert "2 errors" in summary
        assert "1 warning" in summary
        assert ", " in summary  # Check join format

    def test_get_error_summary_all_types(self):
        """Test summary with errors, critical errors, and warnings."""
        container = ModelValidationContainer()
        container.add_error("Normal 1")
        container.add_error("Normal 2")
        container.add_critical_error("Critical")
        container.add_warning("Warning 1")
        container.add_warning("Warning 2")
        summary = container.get_error_summary()
        assert "3 errors (1 critical)" in summary
        assert "2 warnings" in summary


@pytest.mark.unit
class TestModelValidationContainerGetMethods:
    """Test getter methods for error/warning data."""

    def test_get_error_count(self):
        """Test get_error_count returns correct count."""
        container = ModelValidationContainer()
        container.add_error("Error 1")
        container.add_error("Error 2")
        assert container.get_error_count() == 2

    def test_get_critical_error_count(self):
        """Test get_critical_error_count returns correct count."""
        container = ModelValidationContainer()
        container.add_error("Normal")
        container.add_critical_error("Critical 1")
        container.add_critical_error("Critical 2")
        assert container.get_critical_error_count() == 2

    def test_get_warning_count(self):
        """Test get_warning_count returns correct count."""
        container = ModelValidationContainer()
        container.add_warning("Warning 1")
        container.add_warning("Warning 2")
        assert container.get_warning_count() == 2

    def test_get_all_error_messages(self):
        """Test get_all_error_messages returns all messages."""
        container = ModelValidationContainer()
        container.add_error("Error 1")
        container.add_error("Error 2")
        messages = container.get_all_error_messages()
        assert len(messages) == 2
        assert "Error 1" in messages
        assert "Error 2" in messages

    def test_get_critical_error_messages(self):
        """Test get_critical_error_messages returns only critical messages."""
        container = ModelValidationContainer()
        container.add_error("Normal")
        container.add_critical_error("Critical 1")
        container.add_critical_error("Critical 2")
        critical_messages = container.get_critical_error_messages()
        assert len(critical_messages) == 2
        assert "Critical 1" in critical_messages
        assert "Critical 2" in critical_messages
        assert "Normal" not in critical_messages

    def test_get_errors_by_field(self):
        """Test get_errors_by_field filters by field name."""
        container = ModelValidationContainer()
        container.add_error("Error 1", field="field_a")
        container.add_error("Error 2", field="field_b")
        container.add_error("Error 3", field="field_a")

        field_a_errors = container.get_errors_by_field("field_a")
        assert len(field_a_errors) == 2
        assert all(e.field_display_name == "field_a" for e in field_a_errors)


@pytest.mark.unit
class TestModelValidationContainerBulkOperations:
    """Test bulk add and extend operations."""

    def test_add_validation_error(self):
        """Test adding pre-constructed error."""
        container = ModelValidationContainer()
        error = ModelValidationError.create_error(
            message="Pre-constructed", field_name="field"
        )
        container.add_validation_error(error)
        assert len(container.errors) == 1
        assert container.errors[0] is error

    def test_extend_errors(self):
        """Test extending with multiple errors."""
        container = ModelValidationContainer()
        errors = [
            ModelValidationError.create_error(message="Error 1"),
            ModelValidationError.create_error(message="Error 2"),
        ]
        container.extend_errors(errors)
        assert len(container.errors) == 2

    def test_extend_warnings(self):
        """Test extending with multiple warnings."""
        container = ModelValidationContainer()
        warnings = ["Warning 1", "Warning 2", "Warning 3"]
        container.extend_warnings(warnings)
        assert len(container.warnings) == 3

    def test_extend_warnings_with_duplicates(self):
        """Test extending warnings with duplicates (deduplication)."""
        container = ModelValidationContainer()
        container.add_warning("Existing")
        warnings = ["Existing", "New 1", "New 2"]
        container.extend_warnings(warnings)
        # Should have 3 unique warnings
        assert len(container.warnings) == 3


@pytest.mark.unit
class TestModelValidationContainerClearOperations:
    """Test clear operations."""

    def test_clear_all(self):
        """Test clear_all removes both errors and warnings."""
        container = ModelValidationContainer()
        container.add_error("Error")
        container.add_warning("Warning")

        container.clear_all()

        assert len(container.errors) == 0
        assert len(container.warnings) == 0

    def test_clear_errors(self):
        """Test clear_errors removes only errors."""
        container = ModelValidationContainer()
        container.add_error("Error")
        container.add_warning("Warning")

        container.clear_errors()

        assert len(container.errors) == 0
        assert len(container.warnings) == 1

    def test_clear_warnings(self):
        """Test clear_warnings removes only warnings."""
        container = ModelValidationContainer()
        container.add_error("Error")
        container.add_warning("Warning")

        container.clear_warnings()

        assert len(container.errors) == 1
        assert len(container.warnings) == 0


@pytest.mark.unit
class TestModelValidationContainerProtocolMethods:
    """Test protocol method implementations."""

    def test_validate_instance_no_errors(self):
        """Test validate_instance returns True when no errors."""
        container = ModelValidationContainer()
        assert container.validate_instance() is True

    def test_validate_instance_with_errors(self):
        """Test validate_instance returns False when errors exist."""
        container = ModelValidationContainer()
        container.add_error("Error")
        assert container.validate_instance() is False

    def test_validate_instance_with_warnings_only(self):
        """Test validate_instance returns True when only warnings exist."""
        container = ModelValidationContainer()
        container.add_warning("Warning")
        assert container.validate_instance() is True

    def test_serialize(self):
        """Test serialize protocol method."""
        container = ModelValidationContainer()
        container.add_error("Error")
        container.add_warning("Warning")

        serialized = container.serialize()
        assert isinstance(serialized, dict)
        assert "errors" in serialized
        assert "warnings" in serialized


@pytest.mark.unit
class TestModelValidationContainerMergeFrom:
    """Test merge_from operation."""

    def test_merge_from_empty_containers(self):
        """Test merging empty containers."""
        container1 = ModelValidationContainer()
        container2 = ModelValidationContainer()

        container1.merge_from(container2)

        assert len(container1.errors) == 0
        assert len(container1.warnings) == 0

    def test_merge_from_with_errors(self):
        """Test merging errors from another container."""
        container1 = ModelValidationContainer()
        container1.add_error("Error 1")

        container2 = ModelValidationContainer()
        container2.add_error("Error 2")
        container2.add_error("Error 3")

        container1.merge_from(container2)

        assert len(container1.errors) == 3

    def test_merge_from_with_warnings(self):
        """Test merging warnings from another container."""
        container1 = ModelValidationContainer()
        container1.add_warning("Warning 1")

        container2 = ModelValidationContainer()
        container2.add_warning("Warning 2")
        container2.add_warning("Warning 1")  # Duplicate

        container1.merge_from(container2)

        # Warnings are deduplicated by add_warning
        assert len(container1.warnings) == 2

    def test_merge_from_complete(self):
        """Test merging both errors and warnings."""
        container1 = ModelValidationContainer()
        container1.add_error("Error 1")
        container1.add_warning("Warning 1")

        container2 = ModelValidationContainer()
        container2.add_error("Error 2")
        container2.add_critical_error("Critical")
        container2.add_warning("Warning 2")

        container1.merge_from(container2)

        assert len(container1.errors) == 3
        assert len(container1.warnings) == 2
        assert container1.has_critical_errors() is True


@pytest.mark.unit
class TestModelValidationContainerEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_container_summary(self):
        """Test summary of empty container."""
        container = ModelValidationContainer()
        assert container.get_error_summary() == "No validation issues"

    def test_large_number_of_errors(self):
        """Test container with many errors."""
        container = ModelValidationContainer()
        for i in range(100):
            container.add_error(f"Error {i}")

        assert container.get_error_count() == 100
        assert "100 errors" in container.get_error_summary()

    def test_round_trip_serialization(self):
        """Test round-trip serialization/deserialization."""
        container = ModelValidationContainer()
        container.add_error("Error", field="field", error_code="CODE_001")
        container.add_warning("Warning")

        dumped = container.model_dump()
        restored = ModelValidationContainer(**dumped)

        assert restored.get_error_count() == container.get_error_count()
        assert restored.get_warning_count() == container.get_warning_count()

    def test_field_none_handling(self):
        """Test errors with field=None."""
        container = ModelValidationContainer()
        container.add_error("Error", field=None)

        assert len(container.errors) == 1
        assert container.errors[0].field_display_name is None
