"""Tests for the generic factory pattern."""

from typing import Any

import pytest
from pydantic import BaseModel

from omnibase_core.enums.enum_validation_severity import EnumValidationSeverity
from omnibase_core.models.core import (
    ModelCapabilityFactory,
    ModelGenericFactory,
    ModelResultFactory,
    ModelValidationErrorFactory,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError as OnexError


# Test models for factory testing
class SampleResultModel(BaseModel):
    """Test model for result factory testing."""

    success: bool
    exit_code: int = 0
    error_message: str | None = None
    data: Any = None


class CapabilityModelSample(BaseModel):
    """Test model for capability factory testing."""

    name: str
    value: str
    description: str
    deprecated: bool = False
    experimental: bool = False


class SampleValidationModel(BaseModel):
    """Test model for validation factory testing."""

    message: str
    severity: EnumValidationSeverity
    field_name: str | None = None
    error_code: str | None = None


@pytest.mark.unit
class TestModelGenericFactory:
    """Test the basic generic factory functionality."""

    def test_init(self):
        """Test factory initialization."""
        factory = ModelGenericFactory(SampleResultModel)
        assert factory.model_class == SampleResultModel
        assert len(factory.list_factories()) == 0
        assert len(factory.list_builders()) == 0

    def test_register_factory(self):
        """Test factory method registration."""
        factory = ModelGenericFactory(SampleResultModel)

        def create_success() -> SampleResultModel:
            return SampleResultModel(success=True, data="test")

        factory.register_factory("success", create_success)
        assert factory.has_factory("success")
        assert "success" in factory.list_factories()

    def test_register_builder(self):
        """Test builder method registration."""
        factory = ModelGenericFactory(SampleResultModel)

        def build_custom(**kwargs: Any) -> SampleResultModel:
            return SampleResultModel(**kwargs)

        factory.register_builder("custom", build_custom)
        assert factory.has_builder("custom")
        assert "custom" in factory.list_builders()

    def test_create_success(self):
        """Test creating instance with factory method."""
        factory = ModelGenericFactory(SampleResultModel)

        def create_success() -> SampleResultModel:
            return SampleResultModel(success=True, data="test")

        factory.register_factory("success", create_success)
        result = factory.create("success")

        assert result.success is True
        assert result.data == "test"

    def test_create_unknown_factory(self):
        """Test error when using unknown factory."""
        factory = ModelGenericFactory(SampleResultModel)

        with pytest.raises(
            OnexError,
            match="Unknown factory: unknown for SampleResultModel",
        ):
            factory.create("unknown")

    def test_build_success(self):
        """Test building instance with builder method."""
        factory = ModelGenericFactory(SampleResultModel)

        def build_custom(**kwargs: Any) -> SampleResultModel:
            return SampleResultModel(**kwargs)

        factory.register_builder("custom", build_custom)
        result = factory.build("custom", success=False, error_message="test error")

        assert result.success is False
        assert result.error_message == "test error"

    def test_build_unknown_builder(self):
        """Test error when using unknown builder."""
        factory = ModelGenericFactory(SampleResultModel)

        with pytest.raises(
            OnexError,
            match="Unknown builder: unknown for SampleResultModel",
        ):
            factory.build("unknown", success=True)

    def test_create_success_result_utility(self):
        """Test the generic success result utility method."""
        result = ModelGenericFactory.create_success_result(
            SampleResultModel,
            "test_data",
            exit_code=0,
        )

        assert result.success is True
        assert result.data == "test_data"
        assert result.exit_code == 0

    def test_create_error_result_utility(self):
        """Test the generic error result utility method."""
        result = ModelGenericFactory.create_error_result(
            SampleResultModel,
            error="test error",
            exit_code=1,
        )

        assert result.success is False
        assert result.error_message == "test error"
        assert result.exit_code == 1


@pytest.mark.unit
class TestModelResultFactory:
    """Test the specialized result factory."""

    def test_init(self):
        """Test result factory initialization."""
        factory = ModelResultFactory(SampleResultModel)
        assert factory.model_class == SampleResultModel
        assert factory.has_builder("success")
        assert factory.has_builder("error")
        assert factory.has_builder("validation_error")

    def test_build_success_result(self):
        """Test building success result."""
        factory = ModelResultFactory(SampleResultModel)
        result = factory.build("success", data="test_data")

        assert result.success is True
        assert result.exit_code == 0
        assert result.error_message is None
        assert result.data == "test_data"

    def test_build_error_result(self):
        """Test building error result."""
        factory = ModelResultFactory(SampleResultModel)
        result = factory.build("error", error_message="test error", exit_code=5)

        assert result.success is False
        assert result.exit_code == 5
        assert result.error_message == "test error"

    def test_build_validation_error_result(self):
        """Test building validation error result."""
        factory = ModelResultFactory(SampleResultModel)
        result = factory.build("validation_error", error_message="validation failed")

        assert result.success is False
        assert result.exit_code == 2
        assert result.error_message == "validation failed"


@pytest.mark.unit
class TestModelCapabilityFactory:
    """Test the specialized capability factory."""

    def test_init(self):
        """Test capability factory initialization."""
        factory = ModelCapabilityFactory(CapabilityModelSample)
        assert factory.model_class == CapabilityModelSample
        assert factory.has_builder("standard")
        assert factory.has_builder("deprecated")
        assert factory.has_builder("experimental")

    def test_build_standard_capability(self):
        """Test building standard capability."""
        factory = ModelCapabilityFactory(CapabilityModelSample)
        result = factory.build(
            "standard",
            name="TEST_CAPABILITY",
            description="Test capability",
        )

        assert result.name == "TEST_CAPABILITY"
        assert result.value == "test_capability"
        assert result.description == "Test capability"
        assert result.deprecated is False
        assert result.experimental is False

    def test_build_deprecated_capability(self):
        """Test building deprecated capability."""
        factory = ModelCapabilityFactory(CapabilityModelSample)
        result = factory.build(
            "deprecated",
            name="OLD_CAPABILITY",
            description="Old capability",
        )

        assert result.name == "OLD_CAPABILITY"
        assert result.deprecated is True

    def test_build_experimental_capability(self):
        """Test building experimental capability."""
        factory = ModelCapabilityFactory(CapabilityModelSample)
        result = factory.build(
            "experimental",
            name="NEW_CAPABILITY",
            description="New capability",
        )

        assert result.name == "NEW_CAPABILITY"
        assert result.experimental is True


@pytest.mark.unit
class TestModelValidationErrorFactory:
    """Test the specialized validation error factory."""

    def test_init(self):
        """Test validation error factory initialization."""
        factory = ModelValidationErrorFactory(SampleValidationModel)
        assert factory.model_class == SampleValidationModel
        assert factory.has_builder("error")
        assert factory.has_builder("warning")
        assert factory.has_builder("critical")
        assert factory.has_builder("info")

    def test_build_error(self):
        """Test building error validation."""
        factory = ModelValidationErrorFactory(SampleValidationModel)
        result = factory.build("error", message="Test error", field_name="test_field")

        assert result.message == "Test error"
        assert result.severity == EnumValidationSeverity.ERROR
        assert result.field_name == "test_field"

    def test_build_warning(self):
        """Test building warning validation."""
        factory = ModelValidationErrorFactory(SampleValidationModel)
        result = factory.build("warning", message="Test warning")

        assert result.message == "Test warning"
        assert result.severity == EnumValidationSeverity.WARNING

    def test_build_critical(self):
        """Test building critical validation."""
        factory = ModelValidationErrorFactory(SampleValidationModel)
        result = factory.build("critical", message="Critical error")

        assert result.message == "Critical error"
        assert result.severity == EnumValidationSeverity.CRITICAL

    def test_build_info(self):
        """Test building info validation."""
        factory = ModelValidationErrorFactory(SampleValidationModel)
        result = factory.build("info", message="Info message")

        assert result.message == "Info message"
        assert result.severity == EnumValidationSeverity.INFO
