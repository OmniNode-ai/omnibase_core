"""
Tests for ModelValidationContainer and ValidatedModel.

Comprehensive test coverage for the validation error aggregation system
that standardizes validation across all domains.
"""

from omnibase_core.models.validation.model_validation_container import (
    ModelValidationContainer,
)
from omnibase_core.models.validation.model_validation_error import (
    ModelValidationError,
)


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

        container.add_error(
            "Another error",
            field="test_field",
            error_code="TEST_ERROR",
        )
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

    def test_mixed_validation_issues(self):
        """Test container with mixed errors and warnings."""
        container = ModelValidationContainer()

        container.add_error("Standard error")
        container.add_critical_error("Critical error")
        container.add_warning("Warning message")

        assert container.has_errors()
        assert container.has_critical_errors()
        assert container.has_warnings()
        assert container.get_error_count() == 2
        assert container.get_critical_error_count() == 1
        assert container.get_warning_count() == 1
        assert not container.is_valid()

        summary = container.get_error_summary()
        assert "2 errors" in summary
        assert "1 critical" in summary
        assert "1 warning" in summary

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

        # Multiple with critical
        container.add_error("Normal error")
        assert container.get_error_summary() == "2 errors (1 critical)"

        # With warnings
        container.add_warning("Warning")
        assert container.get_error_summary() == "2 errors (1 critical), 1 warning"

        # Only warnings
        container.clear_errors()
        assert container.get_error_summary() == "1 warning"

        # Multiple warnings
        container.add_warning("Another warning")
        assert container.get_error_summary() == "2 warnings"

    def test_field_specific_errors(self):
        """Test field-specific error retrieval."""
        container = ModelValidationContainer()

        container.add_error("Field A error", field="field_a")
        container.add_error("Field B error", field="field_b")
        container.add_error("Another Field A error", field="field_a")
        container.add_error("No field error")

        field_a_errors = container.get_errors_by_field("field_a")
        assert len(field_a_errors) == 2

        field_b_errors = container.get_errors_by_field("field_b")
        assert len(field_b_errors) == 1

        nonexistent_errors = container.get_errors_by_field("nonexistent")
        assert len(nonexistent_errors) == 0

    def test_extend_operations(self):
        """Test extending with multiple errors and warnings."""
        container = ModelValidationContainer()

        errors = [
            ModelValidationError.create_error("Error 1"),
            ModelValidationError.create_critical("Critical Error"),
        ]
        warnings = ["Warning 1", "Warning 2"]

        container.extend_errors(errors)
        container.extend_warnings(warnings)

        assert container.get_error_count() == 2
        assert container.get_critical_error_count() == 1
        assert container.get_warning_count() == 2

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

    def test_clear_operations(self):
        """Test clearing functionality."""
        container = ModelValidationContainer()

        container.add_error("Error")
        container.add_warning("Warning")

        # Clear all
        container.clear_all()
        assert not container.has_errors()
        assert not container.has_warnings()

        # Test partial clearing
        container.add_error("Error")
        container.add_warning("Warning")

        container.clear_errors()
        assert not container.has_errors()
        assert container.has_warnings()

        container.add_error("New error")
        container.clear_warnings()
        assert container.has_errors()
        assert not container.has_warnings()

    def test_to_dict(self):
        """Test dictionary serialization."""
        container = ModelValidationContainer()

        container.add_error("Test error", field="test_field")
        container.add_critical_error("Critical error")
        container.add_warning("Test warning")

        result_dict = container.model_dump()

        assert result_dict["errors"] is not None
        assert result_dict["warnings"] is not None
        assert len(result_dict["errors"]) == 2
        assert len(result_dict["warnings"]) == 1


# NOTE: ValidatedModel class was removed - tests disabled until replacement is implemented
# class TestValidatedModel:
#     """Test the ValidatedModel mixin functionality."""
#
#     def test_basic_validated_model(self):
#         """Test basic ValidatedModel functionality."""
#
#         class TestModel(ValidatedModel):
#             name: str
#
#         model = TestModel(name="test")
#         assert model.is_valid()
#         assert not model.has_validation_errors()
#         assert not model.has_critical_validation_errors()

#     def test_validated_model_with_errors(self):
#         """Test ValidatedModel with validation errors."""
#
#         class TestModel(ValidatedModel):
#             name: str
#             value: int
#
#             def validate_model_data(self) -> None:
#                 if not self.name:
#                     self.validation.add_error("Name is required", field="name")
#                 if self.value < 0:
#                     self.validation.add_critical_error(
#                         "Value must be positive", field="value"
#                     )
#
#         # Valid model
#         valid_model = TestModel(name="test", value=10)
#         assert valid_model.perform_validation()
#         assert valid_model.is_valid()
#
#         # Invalid model
#         invalid_model = TestModel(name="", value=-1)
#         assert not invalid_model.perform_validation()
#         assert not invalid_model.is_valid()
#         assert invalid_model.has_validation_errors()
#         assert invalid_model.has_critical_validation_errors()
#
#     def test_add_validation_methods(self):
#         """Test the convenience methods for adding validation issues."""
#
#         class TestModel(ValidatedModel):
#             name: str
#
#         model = TestModel(name="test")
#
#         model.add_validation_error("Test error", field="name")
#         assert model.has_validation_errors()
#
#         model.add_validation_error("Critical error", field="name", critical=True)
#         assert model.has_critical_validation_errors()
#
#         model.add_validation_warning("Test warning")
#         assert model.validation.has_warnings()
#
#     def test_validation_summary(self):
#         """Test validation summary functionality."""
#
#         class TestModel(ValidatedModel):
#             name: str
#
#         model = TestModel(name="test")
#         model.add_validation_error("Error 1")
#         model.add_validation_warning("Warning 1")
#
#         summary = model.get_validation_summary()
#         assert "1 error" in summary
#         assert "1 warning" in summary
#
#     def test_perform_validation_clears_previous(self):
#         """Test that perform_validation clears previous results."""
#
#         class TestModel(ValidatedModel):
#             name: str
#             should_error: bool
#
#             def validate_model_data(self) -> None:
#                 if self.should_error:
#                     self.validation.add_error("Conditional error")
#
#         model = TestModel(name="test", should_error=True)
#
#         # First validation with error
#         assert not model.perform_validation()
#         assert model.has_validation_errors()
#
#         # Change condition and re-validate
#         model.should_error = False
#         assert model.perform_validation()
#         assert not model.has_validation_errors()  # Previous errors cleared
#
#
# class TestValidationContainerIntegration:
#     """Test integration scenarios with the validation container."""
#
#     def test_complex_validation_scenario(self):
#         """Test a complex validation scenario."""
#
#         class ComplexModel(ValidatedModel):
#             name: str
#             email: str
#             age: int
#             tags: list[str]
#
#             def validate_model_data(self) -> None:
#                 # Name validation
#                 if not self.name.strip():
#                     self.validation.add_critical_error(
#                         "Name cannot be empty", field="name"
#                     )
#                 elif len(self.name) < 2:
#                     self.validation.add_error("Name too short", field="name")
#
#                 # Email validation
#                 if "@" not in self.email:
#                     self.validation.add_error("Invalid email format", field="email")
#
#                 # Age validation
#                 if self.age < 0:
#                     self.validation.add_critical_error(
#                         "Age cannot be negative", field="age"
#                     )
#                 elif self.age < 18:
#                     self.validation.add_warning("User is under 18")
#
#                 # Tags validation
#                 if len(self.tags) == 0:
#                     self.validation.add_warning("No tags specified")
#                 elif len(self.tags) > 10:
#                     self.validation.add_error("Too many tags", field="tags")
#
#         # Test various scenarios
#         scenarios = [
#             # Valid model
#             {
#                 "data": {
#                     "name": "John Doe",
#                     "email": "john@example.com",
#                     "age": 25,
#                     "tags": ["user"],
#                 },
#                 "expected_valid": True,
#                 "expected_errors": 0,
#                 "expected_warnings": 0,
#             },
#             # Invalid email, under 18
#             {
#                 "data": {"name": "Jane", "email": "invalid", "age": 16, "tags": []},
#                 "expected_valid": False,
#                 "expected_errors": 1,
#                 "expected_warnings": 2,
#             },
#             # Critical errors
#             {
#                 "data": {
#                     "name": "",
#                     "email": "test@example.com",
#                     "age": -1,
#                     "tags": ["a"] * 15,
#                 },
#                 "expected_valid": False,
#                 "expected_errors": 3,
#                 "expected_critical": 2,
#                 "expected_warnings": 0,
#             },
#         ]
#
#         for scenario in scenarios:
#             model = ComplexModel(**scenario["data"])
#             is_valid = model.perform_validation()
#
#             assert is_valid == scenario["expected_valid"]
#             assert model.validation.get_error_count() == scenario["expected_errors"]
#             assert model.validation.get_warning_count() == scenario["expected_warnings"]
#
#             if "expected_critical" in scenario:
#                 assert (
#                     model.validation.get_critical_error_count()
#                     == scenario["expected_critical"]
#                 )
#
#     def test_validation_container_serialization(self):
#         """Test that validation containers serialize properly."""
#         container = ModelValidationContainer()
#         container.add_error("Test error", field="test_field", error_code="TEST_001")
#         container.add_critical_error("Critical issue")
#         container.add_warning("Warning message")
#
#         # Test model serialization includes validation
#         class TestModel(ValidatedModel):
#             name: str
#
#         model = TestModel(name="test")
#         model.validation = container
#
#         model_dict = model.model_dump()
#         assert "validation" in model_dict
#         assert "errors" in model_dict["validation"]
#         assert "warnings" in model_dict["validation"]
#         assert len(model_dict["validation"]["errors"]) == 2
#         assert len(model_dict["validation"]["warnings"]) == 1
#
#
# if __name__ == "__main__":
#     pytest.main([__file__])
