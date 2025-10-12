"""
Tests for ModelGenericFactory pattern.

Validates factory registration, instance creation, builder patterns,
error handling, and utility methods following ONEX testing standards.
"""

from typing import Any

import pytest
from pydantic import BaseModel, Field

from omnibase_core.enums.enum_severity_level import EnumSeverityLevel
from omnibase_core.errors.model_onex_error import ModelOnexError as OnexError
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_generic_factory import ModelGenericFactory


# Test models for factory testing
class SampleResult(BaseModel):
    """Sample result model for factory testing."""

    success: bool = Field(description="Operation success status")
    data: ModelSchemaValue | None = Field(default=None, description="Result data")
    error_message: str | None = Field(default=None, description="Error message")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class SampleConfig(BaseModel):
    """Sample configuration model for factory testing."""

    name: str = Field(description="Configuration name")
    value: str = Field(description="Configuration value")
    enabled: bool = Field(default=True, description="Whether config is enabled")
    priority: int = Field(default=1, description="Configuration priority")


class SampleMetrics(BaseModel):
    """Sample metrics model for factory testing."""

    operation: str = Field(description="Operation name")
    duration_ms: float = Field(description="Operation duration")
    success: bool = Field(description="Operation success")
    error_message: str | None = Field(default=None, description="Error message")
    severity: EnumSeverityLevel | None = Field(
        default=None,
        description="Error severity",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional details",
    )


class TestModelGenericFactory:
    """Test basic factory functionality."""

    def test_factory_initialization(self):
        """Test factory initialization with model class."""
        factory = ModelGenericFactory(SampleResult)

        assert factory.model_class == SampleResult
        assert len(factory.list_factories()) == 0
        assert len(factory.list_builders()) == 0

    def test_register_factory_method(self):
        """Test registering simple factory methods."""
        factory = ModelGenericFactory(SampleResult)

        # Register success factory
        def create_success() -> SampleResult:
            return SampleResult(success=True, data=ModelSchemaValue.from_value("test"))

        factory.register_factory("success", create_success)

        assert factory.has_factory("success")
        assert "success" in factory.list_factories()
        assert not factory.has_factory("nonexistent")

    def test_register_builder_method(self):
        """Test registering builder methods with parameters."""
        factory = ModelGenericFactory(SampleConfig)

        def create_config(**kwargs) -> SampleConfig:
            return SampleConfig(**kwargs)

        factory.register_builder("custom", create_config)

        assert factory.has_builder("custom")
        assert "custom" in factory.list_builders()
        assert not factory.has_builder("nonexistent")

    def test_create_instance_success(self):
        """Test successful instance creation using factory."""
        factory = ModelGenericFactory(SampleResult)

        def create_test_result() -> SampleResult:
            return SampleResult(
                success=True,
                data=ModelSchemaValue.from_value("factory_created"),
                metadata={"source": "factory_test"},
            )

        factory.register_factory("test_result", create_test_result)

        result = factory.create("test_result")

        assert isinstance(result, SampleResult)
        assert result.success is True
        assert result.data is not None
        assert result.data.to_value() == "factory_created"
        assert result.metadata["source"] == "factory_test"

    def test_create_instance_unknown_factory(self):
        """Test error handling for unknown factory."""
        from omnibase_core.errors.error_codes import EnumCoreErrorCode

        factory = ModelGenericFactory(SampleResult)

        with pytest.raises(OnexError) as exc_info:
            factory.create("unknown_factory")

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.NOT_FOUND
        assert "Unknown factory: unknown_factory" in str(error)
        assert "SampleResult" in str(error)

    def test_build_instance_success(self):
        """Test successful instance building with parameters."""
        factory = ModelGenericFactory(SampleConfig)

        def build_config(**kwargs) -> SampleConfig:
            return SampleConfig(**kwargs)

        factory.register_builder("dynamic", build_config)

        config = factory.build(
            "dynamic",
            name="test_config",
            value="test_value",
            enabled=False,
            priority=5,
        )

        assert isinstance(config, SampleConfig)
        assert config.name == "test_config"
        assert config.value == "test_value"
        assert config.enabled is False
        assert config.priority == 5

    def test_build_instance_unknown_builder(self):
        """Test error handling for unknown builder."""
        from omnibase_core.errors.error_codes import EnumCoreErrorCode

        factory = ModelGenericFactory(SampleConfig)

        with pytest.raises(OnexError) as exc_info:
            factory.build("unknown_builder", name="test", value="test")

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.NOT_FOUND
        assert "Unknown builder: unknown_builder" in str(error)
        assert "SampleConfig" in str(error)

    def test_multiple_factories_and_builders(self):
        """Test registration and usage of multiple factories and builders."""
        factory = ModelGenericFactory(SampleMetrics)

        # Register multiple factories
        def create_success_metrics() -> SampleMetrics:
            return SampleMetrics(operation="test", duration_ms=100.0, success=True)

        def create_error_metrics() -> SampleMetrics:
            return SampleMetrics(
                operation="test_error",
                duration_ms=50.0,
                success=False,
                error_message="Test error",
                severity=EnumSeverityLevel.ERROR,
            )

        factory.register_factory("success_metrics", create_success_metrics)
        factory.register_factory("error_metrics", create_error_metrics)

        # Register multiple builders
        def build_custom_metrics(**kwargs) -> SampleMetrics:
            return SampleMetrics(**kwargs)

        def build_performance_metrics(**kwargs) -> SampleMetrics:
            defaults = {
                "operation": "performance_test",
                "success": True,
                "details": {"type": "performance"},
            }
            defaults.update(kwargs)
            return SampleMetrics(**defaults)

        factory.register_builder("custom", build_custom_metrics)
        factory.register_builder("performance", build_performance_metrics)

        # Test all registrations
        assert len(factory.list_factories()) == 2
        assert len(factory.list_builders()) == 2

        # Test factory usage
        success = factory.create("success_metrics")
        assert success.success is True
        assert success.operation == "test"

        error = factory.create("error_metrics")
        assert error.success is False
        assert error.error_message == "Test error"

        # Test builder usage
        custom = factory.build(
            "custom",
            operation="custom_op",
            duration_ms=200.0,
            success=True,
        )
        assert custom.operation == "custom_op"
        assert custom.duration_ms == 200.0

        performance = factory.build("performance", duration_ms=150.0)
        assert performance.operation == "performance_test"
        assert performance.details["type"] == "performance"


class TestModelGenericFactoryUtilities:
    """Test utility class methods."""

    def test_create_success_result(self):
        """Test generic success result creation."""
        result = ModelGenericFactory.create_success_result(
            SampleResult,
            result_data=ModelSchemaValue.from_value("success_data"),
            metadata={"created_by": "utility"},
        )

        assert isinstance(result, SampleResult)
        assert result.success is True
        assert result.data is not None
        assert result.data.to_value() == "success_data"
        assert result.metadata["created_by"] == "utility"
        assert result.error_message is None

    def test_create_success_result_no_data(self):
        """Test success result creation without data."""
        result = ModelGenericFactory.create_success_result(
            SampleResult,
            metadata={"source": "test"},
        )

        assert result.success is True
        assert result.data is None
        assert result.metadata["source"] == "test"

    def test_create_error_result(self):
        """Test generic error result creation."""
        result = ModelGenericFactory.create_error_result(
            SampleMetrics,
            error="Test error occurred",
            operation="failed_op",
            duration_ms=75.0,
            severity="error",  # String that should be converted to enum
        )

        assert isinstance(result, SampleMetrics)
        assert result.success is False
        assert result.error_message == "Test error occurred"
        assert result.operation == "failed_op"
        assert result.duration_ms == 75.0
        assert result.severity == EnumSeverityLevel.ERROR

    def test_create_error_result_enum_severity(self):
        """Test error result creation with enum severity."""
        result = ModelGenericFactory.create_error_result(
            SampleMetrics,
            error="Critical error",
            operation="critical_op",
            duration_ms=25.0,
            severity=EnumSeverityLevel.CRITICAL,
        )

        assert result.success is False
        assert result.error_message == "Critical error"
        assert result.severity == EnumSeverityLevel.CRITICAL


class TestModelGenericFactoryIntegration:
    """Test integration scenarios and real-world patterns."""

    def test_factory_with_complex_initialization(self):
        """Test factory with complex object creation logic."""
        factory = ModelGenericFactory(SampleResult)

        def create_complex_result() -> SampleResult:
            # Simulate complex initialization
            metadata = {
                "timestamp": "2024-01-01T12:00:00Z",
                "version": "1.0.0",
                "complexity_level": "high",
            }

            data_value = {
                "processed_items": 100,
                "errors_found": 0,
                "warnings": ["minor optimization possible"],
            }

            return SampleResult(
                success=True,
                data=ModelSchemaValue.from_value(data_value),
                metadata=metadata,
            )

        factory.register_factory("complex", create_complex_result)

        result = factory.create("complex")
        assert result.success is True
        assert result.metadata["complexity_level"] == "high"
        assert result.data.to_value()["processed_items"] == 100

    def test_builder_with_validation_logic(self):
        """Test builder with validation logic."""
        factory = ModelGenericFactory(SampleConfig)

        def build_validated_config(**kwargs) -> SampleConfig:
            # Add validation logic
            if "name" not in kwargs:
                raise ValueError("Configuration name is required")

            if not kwargs["name"].startswith("valid_"):
                kwargs["name"] = f"valid_{kwargs['name']}"

            # Set defaults
            kwargs.setdefault("enabled", True)
            kwargs.setdefault("priority", 1)

            return SampleConfig(**kwargs)

        factory.register_builder("validated", build_validated_config)

        # Test with valid data
        config = factory.build("validated", name="test_config", value="test")
        assert config.name == "valid_test_config"
        assert config.enabled is True

        # Test validation failure
        with pytest.raises(ValueError, match="Configuration name is required"):
            factory.build("validated", value="test_only")

    def test_factory_method_chaining_pattern(self):
        """Test using factory for method chaining patterns."""
        factory = ModelGenericFactory(SampleMetrics)

        # Create base factory
        def create_base_metrics() -> SampleMetrics:
            return SampleMetrics(operation="base", duration_ms=0.0, success=True)

        factory.register_factory("base", create_base_metrics)

        # Use factory in method chain simulation
        base_metrics = factory.create("base")

        # Simulate method chaining by creating modified versions
        modified_metrics = SampleMetrics(
            operation=base_metrics.operation + "_modified",
            duration_ms=base_metrics.duration_ms + 100.0,
            success=base_metrics.success,
            details={"chain_step": 1},
        )

        assert modified_metrics.operation == "base_modified"
        assert modified_metrics.duration_ms == 100.0
        assert modified_metrics.details["chain_step"] == 1

    def test_factory_with_dependency_injection(self):
        """Test factory pattern with dependency injection simulation."""
        factory = ModelGenericFactory(SampleResult)

        # Simulate external dependencies
        class MockService:
            def get_data(self) -> dict[str, Any]:
                return {"service_data": "injected_value"}

        mock_service = MockService()

        # Factory with dependency
        def create_service_result() -> SampleResult:
            service_data = mock_service.get_data()
            return SampleResult(
                success=True,
                data=ModelSchemaValue.from_value(service_data),
                metadata={"source": "injected_service"},
            )

        factory.register_factory("service_result", create_service_result)

        result = factory.create("service_result")
        assert result.data.to_value()["service_data"] == "injected_value"
        assert result.metadata["source"] == "injected_service"

    def test_factory_registration_override(self):
        """Test overriding factory registrations."""
        factory = ModelGenericFactory(SampleResult)

        # Initial registration
        def create_v1() -> SampleResult:
            return SampleResult(success=True, metadata={"version": "v1"})

        factory.register_factory("test", create_v1)
        result_v1 = factory.create("test")
        assert result_v1.metadata["version"] == "v1"

        # Override registration
        def create_v2() -> SampleResult:
            return SampleResult(success=True, metadata={"version": "v2"})

        factory.register_factory("test", create_v2)  # Same name, different impl
        result_v2 = factory.create("test")
        assert result_v2.metadata["version"] == "v2"


class TestModelGenericFactoryErrorHandling:
    """Test error handling and edge cases."""

    def test_factory_method_exception_propagation(self):
        """Test that exceptions in factory methods are properly propagated."""
        factory = ModelGenericFactory(SampleResult)

        def failing_factory() -> SampleResult:
            raise ValueError("Factory method failed")

        factory.register_factory("failing", failing_factory)

        with pytest.raises(ValueError, match="Factory method failed"):
            factory.create("failing")

    def test_builder_method_exception_propagation(self):
        """Test that exceptions in builder methods are properly propagated."""
        factory = ModelGenericFactory(SampleConfig)

        def failing_builder(**kwargs) -> SampleConfig:
            raise RuntimeError("Builder method failed")

        factory.register_builder("failing", failing_builder)

        with pytest.raises(RuntimeError, match="Builder method failed"):
            factory.build("failing", name="test", value="test")

    def test_invalid_model_parameters(self):
        """Test handling of invalid model parameters."""
        factory = ModelGenericFactory(SampleConfig)

        def invalid_builder(**kwargs) -> SampleConfig:
            return SampleConfig(**kwargs)

        factory.register_builder("invalid", invalid_builder)

        # This should raise Pydantic validation error
        with pytest.raises(Exception):  # Could be ValidationError or similar
            factory.build(
                "invalid",
                invalid_field="value",
            )  # SampleConfig doesn't have this field

    def test_empty_factory_and_builder_lists(self):
        """Test behavior with no registered factories or builders."""
        factory = ModelGenericFactory(SampleResult)

        assert factory.list_factories() == []
        assert factory.list_builders() == []
        assert not factory.has_factory("any_name")
        assert not factory.has_builder("any_name")

    def test_factory_type_consistency(self):
        """Test that factory maintains type consistency."""
        # Create factory for specific type
        config_factory = ModelGenericFactory(SampleConfig)

        # Register factory that returns correct type
        def create_config() -> SampleConfig:
            return SampleConfig(name="test", value="test")

        config_factory.register_factory("correct_type", create_config)

        result = config_factory.create("correct_type")
        assert isinstance(result, SampleConfig)
        assert result.name == "test"

    def test_utility_methods_with_incompatible_models(self):
        """Test utility methods with models that don't have expected fields."""

        class IncompatibleModel(BaseModel):
            """Model that doesn't allow extra fields."""

            field1: str = Field(description="Field 1")
            field2: int = Field(description="Field 2")

            model_config = {"extra": "forbid"}

        # This should fail because IncompatibleModel doesn't allow extra fields
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModelGenericFactory.create_success_result(
                IncompatibleModel,
                field1="test",
                field2=42,
            )
