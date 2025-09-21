#!/usr/bin/env python3
"""
Standalone test for ModelValidationContainer to verify functionality.

This test bypasses the circular import issues by importing directly
and demonstrates the validation container capabilities.
"""

import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_validation_severity import EnumValidationSeverity

# Import the validation container directly
from omnibase_core.models.validation.model_validation_container import (
    ModelValidationContainer,
    ValidatedModel,
)
from omnibase_core.models.validation.model_validation_error import ModelValidationError


def test_validation_container_basic():
    """Test basic validation container functionality."""
    print("Testing basic validation container...")

    container = ModelValidationContainer()

    # Test empty container
    assert not container.has_errors()
    assert not container.has_warnings()
    assert container.is_valid()
    assert container.get_error_summary() == "No validation issues"
    print("✓ Empty container test passed")

    # Test adding errors
    container.add_error("Test error", field="test_field")
    assert container.has_errors()
    assert container.get_error_count() == 1
    assert not container.is_valid()
    print("✓ Add error test passed")

    # Test adding warnings
    container.add_warning("Test warning")
    assert container.has_warnings()
    assert container.get_warning_count() == 1
    print("✓ Add warning test passed")

    # Test critical errors
    container.add_critical_error("Critical error")
    assert container.has_critical_errors()
    assert container.get_critical_error_count() == 1
    print("✓ Critical error test passed")

    # Test summary
    summary = container.get_error_summary()
    assert "2 errors" in summary
    assert "1 critical" in summary
    assert "1 warning" in summary
    print(f"✓ Summary test passed: {summary}")


def test_validated_model():
    """Test ValidatedModel mixin."""
    print("\nTesting ValidatedModel mixin...")

    class TestModel(ValidatedModel):
        name: str
        age: int

        def validate_model_data(self) -> None:
            if not self.name:
                self.validation.add_error("Name is required", field="name")
            if self.age < 0:
                self.validation.add_critical_error("Age must be positive", field="age")
            if self.age < 18:
                self.validation.add_warning("User is under 18")

    # Test valid model
    valid_model = TestModel(name="John", age=25)
    assert valid_model.perform_validation()
    assert valid_model.is_valid()
    print("✓ Valid model test passed")

    # Test invalid model
    invalid_model = TestModel(name="", age=-1)
    assert not invalid_model.perform_validation()
    assert not invalid_model.is_valid()
    assert invalid_model.has_validation_errors()
    assert invalid_model.has_critical_validation_errors()
    print("✓ Invalid model test passed")

    # Test model with warnings
    warning_model = TestModel(name="Jane", age=16)
    assert warning_model.perform_validation()  # Valid despite warnings
    assert warning_model.is_valid()
    assert warning_model.validation.has_warnings()
    print("✓ Warning model test passed")


def test_merge_functionality():
    """Test merging validation containers."""
    print("\nTesting merge functionality...")

    container1 = ModelValidationContainer()
    container1.add_error("Error from container 1")
    container1.add_warning("Warning from container 1")

    container2 = ModelValidationContainer()
    container2.add_critical_error("Critical from container 2")
    container2.add_warning("Warning from container 2")

    merged = ModelValidationContainer()
    merged.merge_from(container1)
    merged.merge_from(container2)

    assert merged.get_error_count() == 2
    assert merged.get_critical_error_count() == 1
    assert merged.get_warning_count() == 2
    print("✓ Merge functionality test passed")


def test_field_specific_errors():
    """Test field-specific error handling."""
    print("\nTesting field-specific errors...")

    container = ModelValidationContainer()
    container.add_error("Field A error 1", field="field_a")
    container.add_error("Field A error 2", field="field_a")
    container.add_error("Field B error", field="field_b")
    container.add_error("General error")

    field_a_errors = container.get_errors_by_field("field_a")
    field_b_errors = container.get_errors_by_field("field_b")
    nonexistent_errors = container.get_errors_by_field("nonexistent")

    assert len(field_a_errors) == 2
    assert len(field_b_errors) == 1
    assert len(nonexistent_errors) == 0
    print("✓ Field-specific errors test passed")


def test_serialization():
    """Test dictionary serialization."""
    print("\nTesting serialization...")

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
    print("✓ Serialization test passed")


def demonstrate_usage():
    """Demonstrate practical usage scenarios."""
    print("\n=== DEMONSTRATION: Practical Usage Scenarios ===")

    # Scenario 1: CLI Command Validation
    print("\n1. CLI Command Validation:")

    class MockCliResult(ValidatedModel):
        success: bool
        exit_code: int
        command: str

        def validate_model_data(self) -> None:
            # Validate consistency
            if self.success and self.exit_code != 0:
                self.validation.add_error(
                    "Success flag is True but exit_code is not 0",
                    field="exit_code",
                    error_code="INCONSISTENT_EXIT_CODE",
                )

            if not self.success and self.exit_code == 0:
                self.validation.add_error(
                    "Success flag is False but exit_code is 0",
                    field="success",
                    error_code="INCONSISTENT_SUCCESS_FLAG",
                )

            # Validate command
            if not self.command.strip():
                self.validation.add_critical_error(
                    "Command cannot be empty", field="command"
                )

    # Test inconsistent CLI result
    cli_result = MockCliResult(success=True, exit_code=1, command="test")
    cli_result.perform_validation()
    print(f"   CLI Result Valid: {cli_result.is_valid()}")
    print(f"   CLI Summary: {cli_result.get_validation_summary()}")

    # Scenario 2: User Registration Validation
    print("\n2. User Registration Validation:")

    class UserRegistration(ValidatedModel):
        username: str
        email: str
        password: str
        age: int

        def validate_model_data(self) -> None:
            # Username validation
            if len(self.username) < 3:
                self.validation.add_error("Username too short", field="username")

            # Email validation
            if "@" not in self.email:
                self.validation.add_error("Invalid email format", field="email")

            # Password validation
            if len(self.password) < 8:
                self.validation.add_critical_error(
                    "Password too weak", field="password"
                )

            # Age validation
            if self.age < 13:
                self.validation.add_critical_error(
                    "User must be at least 13", field="age"
                )
            elif self.age < 18:
                self.validation.add_warning("User is under 18")

    # Test user registration
    user = UserRegistration(username="jo", email="invalid", password="123", age=16)
    user.perform_validation()
    print(f"   User Valid: {user.is_valid()}")
    print(f"   User Summary: {user.get_validation_summary()}")
    print(f"   Critical Errors: {user.validation.get_critical_error_count()}")

    # Scenario 3: Batch Validation
    print("\n3. Batch Validation:")

    users = [
        UserRegistration(
            username="alice",
            email="alice@example.com",
            password="strongpass123",
            age=25,
        ),
        UserRegistration(
            username="bob", email="bob@example.com", password="weak", age=17
        ),
        UserRegistration(username="x", email="invalid", password="123", age=12),
    ]

    batch_container = ModelValidationContainer()
    valid_count = 0

    for i, user in enumerate(users):
        user.perform_validation()
        if user.is_valid():
            valid_count += 1
        else:
            # Add user-specific errors to batch
            for error in user.validation.errors:
                batch_container.add_validation_error(
                    ModelValidationError(
                        message=f"User {i}: {error.message}",
                        severity=error.severity,
                        field_name=(
                            f"user_{i}.{error.field_name}"
                            if error.field_name
                            else f"user_{i}"
                        ),
                        error_code=error.error_code,
                    )
                )

    print(f"   Valid Users: {valid_count}/{len(users)}")
    print(f"   Batch Summary: {batch_container.get_error_summary()}")

    print("\n=== ALL TESTS COMPLETED SUCCESSFULLY ===")


def main():
    """Run all tests."""
    print("Running ModelValidationContainer tests...")

    try:
        test_validation_container_basic()
        test_validated_model()
        test_merge_functionality()
        test_field_specific_errors()
        test_serialization()
        demonstrate_usage()

        print("\n🎉 All tests passed! ModelValidationContainer is working correctly.")
        return 0

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
