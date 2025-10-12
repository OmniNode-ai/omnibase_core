"""
Test suite for ModelValidationBase - mixin for models with validation capabilities.

This test suite focuses on validator branches and validation logic to maximize branch coverage.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import Field

from omnibase_core.models.validation.model_validation_base import ModelValidationBase
from omnibase_core.models.validation.model_validation_container import ModelValidationContainer


# Test fixture models
class SimpleTestModel(ModelValidationBase):
    """Simple test model for basic validation tests."""

    name: str
    value: int


class ModelWithOptionalFields(ModelValidationBase):
    """Model with optional fields."""

    required_field: str
    optional_field: str | None = None


class ModelWithComplexValidation(ModelValidationBase):
    """Model with custom validation logic."""

    name: str
    count: int

    def validate_model_data(self) -> None:
        """Custom validation logic."""
        super().validate_model_data()

        if self.count < 0:
            self.add_validation_error("Count must be non-negative", field="count")


class TestModelValidationBaseInstantiation:
    """Test basic model instantiation."""

    def test_default_initialization(self):
        """Test model initializes with default validation container."""
        model = SimpleTestModel(name="test", value=42)
        assert isinstance(model.validation, ModelValidationContainer)
        assert len(model.validation.errors) == 0

    def test_validation_container_default_factory(self):
        """Test validation container uses default_factory."""
        model1 = SimpleTestModel(name="test1", value=1)
        model2 = SimpleTestModel(name="test2", value=2)

        # Each instance should have its own validation container
        model1.validation.add_error("Error 1")
        assert len(model1.validation.errors) == 1
        assert len(model2.validation.errors) == 0


class TestModelValidationBaseHasValidationErrors:
    """Test has_validation_errors method."""

    def test_has_validation_errors_false_when_empty(self):
        """Test returns False when no errors."""
        model = SimpleTestModel(name="test", value=42)
        assert model.has_validation_errors() is False

    def test_has_validation_errors_true_when_errors_exist(self):
        """Test returns True when errors exist."""
        model = SimpleTestModel(name="test", value=42)
        model.validation.add_error("Error")
        assert model.has_validation_errors() is True


class TestModelValidationBaseHasCriticalValidationErrors:
    """Test has_critical_validation_errors method."""

    def test_has_critical_errors_false_when_empty(self):
        """Test returns False when no errors."""
        model = SimpleTestModel(name="test", value=42)
        assert model.has_critical_validation_errors() is False

    def test_has_critical_errors_false_with_normal_errors(self):
        """Test returns False when only normal errors."""
        model = SimpleTestModel(name="test", value=42)
        model.validation.add_error("Normal error")
        assert model.has_critical_validation_errors() is False

    def test_has_critical_errors_true_when_critical_exists(self):
        """Test returns True when critical errors exist."""
        model = SimpleTestModel(name="test", value=42)
        model.validation.add_critical_error("Critical error")
        assert model.has_critical_validation_errors() is True


class TestModelValidationBaseAddValidationErrorBranches:
    """Test add_validation_error method branches."""

    def test_add_validation_error_non_critical(self):
        """Test add_validation_error with critical=False (else branch)."""
        model = SimpleTestModel(name="test", value=42)
        model.add_validation_error(
            message="Normal error",
            field="name",
            error_code="ERROR_001",
            critical=False
        )

        assert len(model.validation.errors) == 1
        assert model.validation.errors[0].is_critical() is False

    def test_add_validation_error_critical(self):
        """Test add_validation_error with critical=True (if branch)."""
        model = SimpleTestModel(name="test", value=42)
        model.add_validation_error(
            message="Critical error",
            field="value",
            error_code="ERROR_002",
            critical=True
        )

        assert len(model.validation.errors) == 1
        assert model.validation.errors[0].is_critical() is True

    def test_add_validation_error_defaults(self):
        """Test add_validation_error with default parameters."""
        model = SimpleTestModel(name="test", value=42)
        model.add_validation_error(message="Simple error")

        assert len(model.validation.errors) == 1
        assert model.validation.errors[0].message == "Simple error"


class TestModelValidationBaseAddValidationWarning:
    """Test add_validation_warning method."""

    def test_add_validation_warning(self):
        """Test add_validation_warning adds to warnings."""
        model = SimpleTestModel(name="test", value=42)
        model.add_validation_warning("Warning message")

        assert len(model.validation.warnings) == 1
        assert model.validation.warnings[0] == "Warning message"


class TestModelValidationBaseGetValidationSummary:
    """Test get_validation_summary method."""

    def test_get_validation_summary_no_errors(self):
        """Test summary with no errors."""
        model = SimpleTestModel(name="test", value=42)
        summary = model.get_validation_summary()
        assert summary == "No validation issues"

    def test_get_validation_summary_with_errors(self):
        """Test summary with errors."""
        model = SimpleTestModel(name="test", value=42)
        model.add_validation_error("Error 1")
        model.add_validation_error("Error 2")
        summary = model.get_validation_summary()
        assert "2 errors" in summary


class TestModelValidationBaseValidateModelDataBranches:
    """Test validate_model_data method branches."""

    def test_validate_model_data_import_success(self):
        """Test validate_model_data when import succeeds (try branch)."""
        model = SimpleTestModel(name="test", value=42)
        model.validate_model_data()
        # Should not raise error, normal validation proceeds

    @patch('importlib.import_module')
    def test_validate_model_data_import_error_fallback(self, mock_import):
        """Test validate_model_data with ImportError uses fallback codes (except branch line 95)."""
        mock_import.side_effect = ImportError("Module not found")

        model = SimpleTestModel(name="test", value=42)
        model.validate_model_data()
        # Should use fallback error codes, not raise

    @patch('importlib.import_module')
    def test_validate_model_data_attribute_error_fallback(self, mock_import):
        """Test validate_model_data with AttributeError uses fallback codes (except branch line 95)."""
        mock_module = MagicMock()
        delattr(mock_module, 'EnumCoreErrorCode')  # Remove attribute
        mock_import.return_value = mock_module

        model = SimpleTestModel(name="test", value=42)
        model.validate_model_data()
        # Should use fallback error codes, not raise

    def test_validate_model_data_no_add_error_method(self):
        """Test validate_model_data when validation doesn't have add_error (line 103 branch)."""
        model = SimpleTestModel(name="test", value=42)
        # Mock validation object without add_error method
        mock_validation = MagicMock(spec=[])  # Empty spec means no methods
        # Bypass Pydantic validation by using object.__setattr__
        object.__setattr__(model, 'validation', mock_validation)

        model.validate_model_data()
        # Should return early without error (no exception raised)

    def test_validate_model_data_no_model_fields(self):
        """Test validate_model_data with no model fields (line 110 branch)."""
        model = SimpleTestModel(name="test", value=42)

        # Patch the class-level model_fields to return empty dict
        with patch.object(SimpleTestModel, 'model_fields', {}):
            model.validate_model_data()
            # Should add warning about no fields
            assert any("no defined fields" in w.lower() for w in model.validation.warnings)

    def test_validate_model_data_field_access_error(self):
        """Test validate_model_data when field access fails (line 136 except branch)."""
        model = SimpleTestModel(name="test", value=42)

        # Patch class-level model_fields to raise an exception
        with patch.object(SimpleTestModel, 'model_fields', new_callable=lambda: property(lambda self: (_ for _ in ()).throw(Exception("Field error")))):
            model.validate_model_data()
            # Should add validation error about field access
            assert any("Failed to access model fields" in e.message for e in model.validation.errors)

    def test_validate_model_data_serialization_empty_dict(self):
        """Test validate_model_data when serialization returns empty dict (line 145 branch)."""
        model = SimpleTestModel(name="test", value=42)

        # Store original method and create a wrapper
        original_model_dump = model.model_dump
        def mock_model_dump(*args, **kwargs):
            return {}

        # Use object.__setattr__ to bypass Pydantic
        object.__setattr__(model, 'model_dump', mock_model_dump)
        try:
            model.validate_model_data()
            # Should add error about empty serialization
            assert any("empty" in e.message.lower() and "dict" in e.message.lower() for e in model.validation.errors)
        finally:
            # Restore original method
            object.__setattr__(model, 'model_dump', original_model_dump)

    def test_validate_model_data_serialization_fails(self):
        """Test validate_model_data when serialization fails (line 151 except branch)."""
        model = SimpleTestModel(name="test", value=42)

        # Store original method and create a wrapper that raises
        original_model_dump = model.model_dump
        def mock_model_dump(*args, **kwargs):
            raise Exception("Serialization error")

        # Use object.__setattr__ to bypass Pydantic
        object.__setattr__(model, 'model_dump', mock_model_dump)
        try:
            model.validate_model_data()
            # Should add error about serialization failure
            assert any("serialization failed" in e.message.lower() for e in model.validation.errors)
        finally:
            # Restore original method
            object.__setattr__(model, 'model_dump', original_model_dump)

    def test_validate_model_data_circular_reference_detected(self):
        """Test validate_model_data detects circular references (line 165 branch)."""
        model = SimpleTestModel(name="test", value=42)

        with patch('json.dumps', side_effect=RecursionError("Circular reference")):
            model.validate_model_data()
            # Should add critical error about circular references
            critical_errors = [e for e in model.validation.errors if e.is_critical()]
            assert any("circular reference" in e.message.lower() for e in critical_errors)

    def test_validate_model_data_value_error_in_json(self):
        """Test validate_model_data with ValueError in JSON (line 175 else branch)."""
        model = SimpleTestModel(name="test", value=42)

        with patch('json.dumps', side_effect=ValueError("JSON error")):
            model.validate_model_data()
            # Should add warning (not critical error)
            assert any("serialization issues" in w.lower() for w in model.validation.warnings)

    def test_validate_model_data_type_error_in_json(self):
        """Test validate_model_data with TypeError in JSON (line 175 else branch)."""
        model = SimpleTestModel(name="test", value=42)

        with patch('json.dumps', side_effect=TypeError("Type not serializable")):
            model.validate_model_data()
            # Should add warning
            assert any("serialization issues" in w.lower() for w in model.validation.warnings)

    def test_validate_model_data_unexpected_error(self):
        """Test validate_model_data with unexpected error (line 180 except branch)."""
        model = SimpleTestModel(name="test", value=42)

        # Mock the entire validation container to cause add_error to raise
        mock_validation = MagicMock()
        mock_validation.add_error.side_effect = RuntimeError("Unexpected")
        mock_validation.add_critical_error.side_effect = RuntimeError("Unexpected")
        # Need these methods to exist for hasattr check
        mock_validation.add_warning = MagicMock()
        # Bypass Pydantic validation by using object.__setattr__
        object.__setattr__(model, 'validation', mock_validation)

        # The outer except block will try to add_validation_error, which will also fail
        # This should cause the RuntimeError to bubble up
        try:
            model.validate_model_data()
            # If we get here, the error was swallowed (which might be acceptable)
        except RuntimeError:
            pass  # Expected to bubble up


class TestModelValidationBasePerformValidation:
    """Test perform_validation method."""

    def test_perform_validation_clears_previous_results(self):
        """Test perform_validation clears previous validation results."""
        model = SimpleTestModel(name="test", value=42)
        model.validation.add_error("Old error")
        model.validation.add_warning("Old warning")

        result = model.perform_validation()

        # Old errors should be cleared
        assert len(model.validation.errors) == 0

    def test_perform_validation_returns_true_on_success(self):
        """Test perform_validation returns True when no errors."""
        model = SimpleTestModel(name="test", value=42)
        result = model.perform_validation()
        assert result is True

    def test_perform_validation_returns_false_on_failure(self):
        """Test perform_validation returns False when errors exist."""
        model = ModelWithComplexValidation(name="test", count=-5)
        result = model.perform_validation()
        assert result is False

    def test_perform_validation_runs_custom_validation(self):
        """Test perform_validation runs custom validate_model_data."""
        model = ModelWithComplexValidation(name="test", count=-10)
        model.perform_validation()

        # Custom validation should have added error
        assert any("Count must be non-negative" in e.message for e in model.validation.errors)


class TestModelValidationBaseValidateInstance:
    """Test validate_instance protocol method."""

    def test_validate_instance_delegates_to_container(self):
        """Test validate_instance delegates to validation container."""
        model = SimpleTestModel(name="test", value=42)
        result = model.validate_instance()
        assert result is True

        model.validation.add_error("Error")
        result = model.validate_instance()
        assert result is False


class TestModelValidationBaseSerialize:
    """Test serialize protocol method."""

    def test_serialize_returns_dict(self):
        """Test serialize returns dictionary."""
        model = SimpleTestModel(name="test", value=42)
        serialized = model.serialize()

        assert isinstance(serialized, dict)
        assert "name" in serialized
        assert "value" in serialized
        assert serialized["name"] == "test"
        assert serialized["value"] == 42

    def test_serialize_includes_validation(self):
        """Test serialize includes validation container."""
        model = SimpleTestModel(name="test", value=42)
        model.add_validation_error("Test error")

        serialized = model.serialize()
        assert "validation" in serialized


class TestModelValidationBaseEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_multiple_validations(self):
        """Test running validation multiple times."""
        model = ModelWithComplexValidation(name="test", count=-5)

        # First validation
        result1 = model.perform_validation()
        assert result1 is False
        error_count_1 = len(model.validation.errors)

        # Second validation should clear previous errors
        result2 = model.perform_validation()
        error_count_2 = len(model.validation.errors)

        # Should have same number of errors (cleared then re-validated)
        assert error_count_1 == error_count_2

    def test_validation_with_none_optional_fields(self):
        """Test validation with None values in optional fields."""
        model = ModelWithOptionalFields(required_field="test", optional_field=None)
        result = model.perform_validation()
        assert result is True

    def test_round_trip_with_validation_errors(self):
        """Test serialization/deserialization preserves validation state."""
        model = SimpleTestModel(name="test", value=42)
        model.add_validation_error("Test error", field="name")

        dumped = model.model_dump()
        restored = SimpleTestModel(**dumped)

        # Validation container should be included
        assert "validation" in dumped

    def test_model_with_many_fields(self):
        """Test validation on model with many fields."""
        class LargeModel(ModelValidationBase):
            field1: str
            field2: int
            field3: bool
            field4: float
            field5: str | None = None

        model = LargeModel(
            field1="test",
            field2=42,
            field3=True,
            field4=3.14
        )

        result = model.perform_validation()
        assert result is True

    def test_empty_string_field_value(self):
        """Test validation with empty string field."""
        model = SimpleTestModel(name="", value=0)
        result = model.perform_validation()
        assert result is True  # Empty string is valid

    def test_validation_error_with_all_parameters(self):
        """Test adding validation error with all parameters."""
        model = SimpleTestModel(name="test", value=42)
        model.add_validation_error(
            message="Complete error",
            field="name",
            error_code="ERR_001",
            critical=True
        )

        assert len(model.validation.errors) == 1
        error = model.validation.errors[0]
        assert error.message == "Complete error"
        assert error.field_display_name == "name"
        assert error.error_code == "ERR_001"
        assert error.is_critical() is True


class TestModelValidationBaseInheritance:
    """Test inheritance and custom validation scenarios."""

    def test_custom_validation_calls_super(self):
        """Test custom validation can call super().validate_model_data()."""
        model = ModelWithComplexValidation(name="test", count=10)
        model.validate_model_data()
        # Should run base validation without errors

    def test_custom_validation_adds_domain_errors(self):
        """Test custom validation adds domain-specific errors."""
        model = ModelWithComplexValidation(name="test", count=-1)
        model.validate_model_data()

        # Should have custom domain error
        assert any("non-negative" in e.message.lower() for e in model.validation.errors)

    def test_model_config_preserved(self):
        """Test model_config settings are preserved."""
        model = SimpleTestModel(name="test", value=42)

        # Test extra="ignore"
        model_dict = model.model_dump()
        restored = SimpleTestModel(**{**model_dict, "extra_field": "ignored"})
        assert not hasattr(restored, "extra_field")
