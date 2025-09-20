"""
Simplified tests for ModelValidationContainer that avoid circular imports.

This test file focuses on the core validation container functionality
without importing complex models that have circular dependencies.
"""

import pytest
from pydantic import BaseModel, Field

# Direct imports to avoid circular dependencies
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from omnibase_core.models.validation.model_validation_container import (
    ModelValidationContainer,
    ValidatedModel,
)
from omnibase_core.models.validation.model_validation_error import ModelValidationError
from omnibase_core.enums.enum_validation_severity import EnumValidationSeverity


class TestModelValidationContainer:
    """Test the ModelValidationContainer functionality."""

    def test_empty_container(self):
        """Test empty validation container."""
        container = ModelValidationContainer()

        assert not container.has_errors()
        assert not container.has_critical_errors()
        assert not container.has_warnings()
        assert container.get_error_count() == 0
        assert container.get_critical_error_count() == 0
        assert container.get_warning_count() == 0
        assert container.is_valid()
        assert container.get_error_summary() == "No validation issues"

    def test_add_error(self):
        """Test adding standard errors."""
        container = ModelValidationContainer()

        container.add_error("Test error message")
        assert container.has_errors()
        assert container.get_error_count() == 1
        assert not container.is_valid()

        container.add_error("Another error", field="test_field", error_code="TEST_ERROR")
        assert container.get_error_count() == 2

        error_messages = container.get_all_error_messages()
        assert "Test error message" in error_messages
        assert "Another error" in error_messages

    def test_add_critical_error(self):
        """Test adding critical errors."""
        container = ModelValidationContainer()

        container.add_critical_error("Critical error", field="critical_field")
        assert container.has_errors()
        assert container.has_critical_errors()
        assert container.get_critical_error_count() == 1

        critical_messages = container.get_critical_error_messages()
        assert "Critical error" in critical_messages

    def test_add_warning(self):
        """Test adding warnings."""
        container = ModelValidationContainer()

        container.add_warning("Warning message")
        assert container.has_warnings()
        assert container.get_warning_count() == 1
        assert container.is_valid()  # Warnings don't affect validity

        # Test deduplication
        container.add_warning("Warning message")
        assert container.get_warning_count() == 1

        container.add_warning("Another warning")
        assert container.get_warning_count() == 2

    def test_error_summary_formatting(self):
        """Test error summary formatting for different scenarios."""
        container = ModelValidationContainer()

        # Single error
        container.add_error("Error")
        assert container.get_error_summary() == "1 error"

        # Multiple errors
        container.clear_all()
        container.add_error("Error 1")
        container.add_error("Error 2")
        assert container.get_error_summary() == "2 errors"

        # Critical error
        container.clear_all()
        container.add_critical_error("Critical")
        assert container.get_error_summary() == "1 error (1 critical)"

        # With warnings
        container.add_warning("Warning")
        assert container.get_error_summary() == "1 error (1 critical), 1 warning"

    def test_merge_from(self):
        """Test merging validation results."""
        container1 = ModelValidationContainer()
        container1.add_error("Error from container 1")
        container1.add_warning("Warning from container 1")

        container2 = ModelValidationContainer()
        container2.add_critical_error("Critical from container 2")
        container2.add_warning("Warning from container 2")
        container2.add_warning("Warning from container 1")  # Duplicate

        merged = ModelValidationContainer()
        merged.merge_from(container1)
        merged.merge_from(container2)

        assert merged.get_error_count() == 2
        assert merged.get_critical_error_count() == 1
        assert merged.get_warning_count() == 2  # Deduplicated

    def test_to_dict(self):
        """Test dictionary serialization."""
        container = ModelValidationContainer()

        container.add_error("Test error", field="test_field", error_code="TEST_001")
        container.add_critical_error("Critical error")
        container.add_warning("Test warning")

        result_dict = container.to_dict()

        assert result_dict["error_count"] == 2
        assert result_dict["critical_error_count"] == 1
        assert result_dict["warning_count"] == 1
        assert result_dict["is_valid"] is False
        assert "summary" in result_dict
        assert len(result_dict["errors"]) == 2
        assert len(result_dict["warnings"]) == 1


class TestValidatedModel:
    """Test the ValidatedModel mixin functionality."""

    def test_basic_validated_model(self):
        """Test basic ValidatedModel functionality."""
        class TestModel(ValidatedModel):
            name: str

        model = TestModel(name="test")
        assert model.is_valid()
        assert not model.has_validation_errors()
        assert not model.has_critical_validation_errors()

    def test_validated_model_with_custom_validation(self):
        """Test ValidatedModel with custom validation logic."""
        class TestModel(ValidatedModel):
            name: str
            value: int

            def validate_model_data(self) -> None:
                if not self.name:
                    self.validation.add_error("Name is required", field="name")
                if self.value < 0:
                    self.validation.add_critical_error("Value must be positive", field="value")

        # Valid model
        valid_model = TestModel(name="test", value=10)
        assert valid_model.perform_validation()
        assert valid_model.is_valid()

        # Invalid model
        invalid_model = TestModel(name="", value=-1)
        assert not invalid_model.perform_validation()
        assert not invalid_model.is_valid()
        assert invalid_model.has_validation_errors()
        assert invalid_model.has_critical_validation_errors()

    def test_add_validation_methods(self):
        """Test the convenience methods for adding validation issues."""
        class TestModel(ValidatedModel):
            name: str

        model = TestModel(name="test")

        model.add_validation_error("Test error", field="name")
        assert model.has_validation_errors()

        model.add_validation_error("Critical error", field="name", critical=True)
        assert model.has_critical_validation_errors()

        model.add_validation_warning("Test warning")
        assert model.validation.has_warnings()

    def test_perform_validation_clears_previous(self):
        """Test that perform_validation clears previous results."""
        class TestModel(ValidatedModel):
            name: str
            should_error: bool

            def validate_model_data(self) -> None:
                if self.should_error:
                    self.validation.add_error("Conditional error")

        model = TestModel(name="test", should_error=True)

        # First validation with error
        assert not model.perform_validation()
        assert model.has_validation_errors()

        # Change condition and re-validate
        model.should_error = False
        assert model.perform_validation()
        assert not model.has_validation_errors()  # Previous errors cleared


def test_complex_validation_scenario():
    """Test a complex validation scenario."""
    class ComplexModel(ValidatedModel):
        name: str
        email: str
        age: int
        tags: list[str] = Field(default_factory=list)

        def validate_model_data(self) -> None:
            # Name validation
            if not self.name.strip():
                self.validation.add_critical_error("Name cannot be empty", field="name")
            elif len(self.name) < 2:
                self.validation.add_error("Name too short", field="name")

            # Email validation
            if "@" not in self.email:
                self.validation.add_error("Invalid email format", field="email")

            # Age validation
            if self.age < 0:
                self.validation.add_critical_error("Age cannot be negative", field="age")
            elif self.age < 18:
                self.validation.add_warning("User is under 18")

            # Tags validation
            if len(self.tags) == 0:
                self.validation.add_warning("No tags specified")
            elif len(self.tags) > 10:
                self.validation.add_error("Too many tags", field="tags")

    # Test valid model
    valid_model = ComplexModel(name="John Doe", email="john@example.com", age=25, tags=["user"])
    assert valid_model.perform_validation()
    assert valid_model.is_valid()

    # Test invalid model
    invalid_model = ComplexModel(name="", email="invalid", age=-1, tags=["a"] * 15)
    assert not invalid_model.perform_validation()
    assert not invalid_model.is_valid()
    assert invalid_model.validation.get_critical_error_count() == 2  # Name and age
    assert invalid_model.validation.get_error_count() == 3  # Name, age, tags


if __name__ == "__main__":
    pytest.main([__file__, "-v"])