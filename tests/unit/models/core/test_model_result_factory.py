# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for ModelResultFactory.

Comprehensive tests for result factory pattern including success/error builders.
"""

import pytest
from pydantic import BaseModel, Field

from omnibase_core.models.core.model_result_factory import ModelResultFactory


# Sample models for testing
class SampleResultModel(BaseModel):
    """Sample model for result factory testing."""

    success: bool = Field(default=False)
    exit_code: int = Field(default=1)
    error_message: str | None = Field(default=None)
    data: str | None = Field(default=None)
    count: int = Field(default=0)


class MinimalResultModel(BaseModel):
    """Minimal result model."""

    success: bool
    exit_code: int
    error_message: str | None = None


@pytest.mark.unit
class TestModelResultFactory:
    """Test suite for ModelResultFactory."""

    def test_initialization(self):
        """Test factory initialization."""
        factory = ModelResultFactory(SampleResultModel)

        assert factory.model_class == SampleResultModel
        assert factory.has_builder("success")
        assert factory.has_builder("error")
        assert factory.has_builder("validation_error")

    def test_build_success_result_defaults(self):
        """Test building success result with defaults."""
        factory = ModelResultFactory(SampleResultModel)

        result = factory.build("success")

        assert isinstance(result, SampleResultModel)
        assert result.success is True
        assert result.exit_code == 0
        assert result.error_message is None
        assert result.data is None
        assert result.count == 0

    def test_build_success_result_with_data(self):
        """Test building success result with additional data."""
        factory = ModelResultFactory(SampleResultModel)

        result = factory.build("success", data="test data", count=5)

        assert result.success is True
        assert result.exit_code == 0
        assert result.error_message is None
        assert result.data == "test data"
        assert result.count == 5

    def test_build_success_result_custom_exit_code(self):
        """Test building success result with custom exit code."""
        factory = ModelResultFactory(SampleResultModel)

        result = factory.build("success", exit_code=100)

        assert result.success is True
        assert result.exit_code == 100
        assert result.error_message is None

    def test_build_error_result_defaults(self):
        """Test building error result with defaults."""
        factory = ModelResultFactory(SampleResultModel)

        result = factory.build("error")

        assert isinstance(result, SampleResultModel)
        assert result.success is False
        assert result.exit_code == 1
        assert result.error_message == "Unknown error"

    def test_build_error_result_with_message(self):
        """Test building error result with custom message."""
        factory = ModelResultFactory(SampleResultModel)

        result = factory.build("error", error_message="Custom error message")

        assert result.success is False
        assert result.exit_code == 1
        assert result.error_message == "Custom error message"

    def test_build_error_result_custom_exit_code(self):
        """Test building error result with custom exit code."""
        factory = ModelResultFactory(SampleResultModel)

        result = factory.build("error", exit_code=500, error_message="Server error")

        assert result.success is False
        assert result.exit_code == 500
        assert result.error_message == "Server error"

    def test_build_error_result_with_data(self):
        """Test building error result with additional data."""
        factory = ModelResultFactory(SampleResultModel)

        result = factory.build(
            "error", error_message="Error occurred", data="error context", count=3
        )

        assert result.success is False
        assert result.error_message == "Error occurred"
        assert result.data == "error context"
        assert result.count == 3

    def test_build_validation_error_defaults(self):
        """Test building validation error with defaults."""
        factory = ModelResultFactory(SampleResultModel)

        result = factory.build("validation_error")

        assert isinstance(result, SampleResultModel)
        assert result.success is False
        assert result.exit_code == 2
        assert result.error_message == "Validation failed"

    def test_build_validation_error_with_message(self):
        """Test building validation error with custom message."""
        factory = ModelResultFactory(SampleResultModel)

        result = factory.build("validation_error", error_message="Invalid input format")

        assert result.success is False
        assert result.exit_code == 2
        assert result.error_message == "Invalid input format"

    def test_build_validation_error_custom_exit_code(self):
        """Test building validation error with custom exit code."""
        factory = ModelResultFactory(SampleResultModel)

        result = factory.build(
            "validation_error", exit_code=400, error_message="Bad request"
        )

        assert result.success is False
        assert result.exit_code == 400
        assert result.error_message == "Bad request"

    def test_build_with_minimal_model(self):
        """Test factory with minimal result model."""
        factory = ModelResultFactory(MinimalResultModel)

        # Success
        success_result = factory.build("success")
        assert success_result.success is True
        assert success_result.exit_code == 0
        assert success_result.error_message is None

        # Error
        error_result = factory.build("error", error_message="Failed")
        assert error_result.success is False
        assert error_result.exit_code == 1
        assert error_result.error_message == "Failed"

        # Validation error
        validation_result = factory.build("validation_error")
        assert validation_result.success is False
        assert validation_result.exit_code == 2
        assert validation_result.error_message == "Validation failed"

    def test_field_filtering_success(self):
        """Test that conflicting fields are filtered in success builder."""
        factory = ModelResultFactory(SampleResultModel)

        # These should be filtered and replaced with success values
        result = factory.build(
            "success",
            success=False,  # Should be ignored
            error_message="ignored",  # Should be ignored
            data="kept",
        )

        assert result.success is True  # Forced by builder
        assert result.error_message is None  # Forced by builder
        assert result.data == "kept"  # Not filtered

    def test_field_filtering_error(self):
        """Test that conflicting fields are filtered in error builder."""
        factory = ModelResultFactory(SampleResultModel)

        # These should be filtered and replaced with error values
        result = factory.build(
            "error",
            success=True,  # Should be ignored
            exit_code=999,  # Should be kept
            error_message="custom error",  # Should be kept
            data="kept",
        )

        assert result.success is False  # Forced by builder
        assert result.exit_code == 999  # Kept from kwargs
        assert result.error_message == "custom error"  # Kept from kwargs
        assert result.data == "kept"  # Not filtered

    def test_inheritance_from_generic_factory(self):
        """Test that ResultFactory inherits GenericFactory capabilities."""
        factory = ModelResultFactory(SampleResultModel)

        # Should inherit builder registration and build methods
        assert hasattr(factory, "build")
        assert hasattr(factory, "register_builder")
        assert hasattr(factory, "_builders")  # Private attribute
        # Can also check via method
        assert factory.has_builder("success")

    def test_create_method_for_success(self):
        """Test that model_class can be instantiated directly."""
        factory = ModelResultFactory(SampleResultModel)

        # Direct instantiation via model_class
        result = factory.model_class(
            success=True, exit_code=0, error_message=None, data="test"
        )

        assert result.success is True
        assert result.exit_code == 0
        assert result.data == "test"

    def test_builder_pattern_consistency(self):
        """Test that all builders follow consistent patterns."""
        factory = ModelResultFactory(SampleResultModel)

        success_result = factory.build("success", count=1)
        error_result = factory.build("error", count=2)
        validation_result = factory.build("validation_error", count=3)

        # All should preserve non-conflicting fields
        assert success_result.count == 1
        assert error_result.count == 2
        assert validation_result.count == 3

        # All should have proper success flag
        assert success_result.success is True
        assert error_result.success is False
        assert validation_result.success is False

        # Exit codes should be consistent
        assert success_result.exit_code == 0
        assert error_result.exit_code == 1
        assert validation_result.exit_code == 2

    def test_multiple_factories_independence(self):
        """Test that multiple factory instances are independent."""
        factory1 = ModelResultFactory(SampleResultModel)
        factory2 = ModelResultFactory(MinimalResultModel)

        result1 = factory1.build("success", data="factory1")
        result2 = factory2.build("success")

        assert isinstance(result1, SampleResultModel)
        assert isinstance(result2, MinimalResultModel)
        assert result1.data == "factory1"
        assert not hasattr(result2, "data")


@pytest.mark.unit
class TestResultFactoryEdgeCases:
    """Edge case tests for ModelResultFactory."""

    def test_empty_kwargs(self):
        """Test builders with empty kwargs."""
        factory = ModelResultFactory(SampleResultModel)

        success = factory.build("success")
        error = factory.build("error")
        validation = factory.build("validation_error")

        assert success.success is True
        assert error.success is False
        assert validation.success is False

    def test_none_values(self):
        """Test builders with None values."""
        factory = ModelResultFactory(SampleResultModel)

        result = factory.build("success", data=None, count=0)

        assert result.success is True
        assert result.data is None
        assert result.count == 0

    def test_error_message_variations(self):
        """Test various error message formats."""
        factory = ModelResultFactory(SampleResultModel)

        # Empty string
        result1 = factory.build("error", error_message="")
        assert result1.error_message == ""

        # Long message
        long_message = "x" * 1000
        result2 = factory.build("error", error_message=long_message)
        assert result2.error_message == long_message

        # Special characters
        result3 = factory.build("error", error_message="Error: \n\t\r\"'")
        assert result3.error_message == "Error: \n\t\r\"'"
