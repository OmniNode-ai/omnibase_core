"""Tests for ModelONEXContainer service registry initialization API.

This module tests the initialize_service_registry() method and service_registry
property of ModelONEXContainer, covering:
- Default and custom configuration initialization
- Error handling for already-initialized registries
- Error handling for accessing uninitialized registries
- Property access patterns after initialization
"""

import pytest

from omnibase_core.container.container_service_registry import ServiceRegistry
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    ModelServiceRegistryConfig,
    create_default_registry_config,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@pytest.mark.unit
class TestInitializeServiceRegistryWithDefaultConfig:
    """Tests for initialize_service_registry with default configuration."""

    def test_initialize_service_registry_with_default_config(self) -> None:
        """Verify initialize_service_registry creates registry with default config.

        When called without arguments on a container with enable_service_registry=False,
        the method should create a ServiceRegistry with default configuration and
        make it accessible via the service_registry property.
        """
        # Arrange
        container = ModelONEXContainer(enable_service_registry=False)

        # Act
        result = container.initialize_service_registry()

        # Assert
        assert isinstance(result, ServiceRegistry)
        assert container.service_registry is result
        assert result.config.registry_name == "omnibase_core_registry"


@pytest.mark.unit
class TestInitializeServiceRegistryWithCustomConfig:
    """Tests for initialize_service_registry with custom configuration."""

    def test_initialize_service_registry_with_custom_config(self) -> None:
        """Verify initialize_service_registry applies custom configuration.

        When called with a custom ModelServiceRegistryConfig, the created
        ServiceRegistry should use the provided configuration values.
        """
        # Arrange
        container = ModelONEXContainer(enable_service_registry=False)
        custom_config = ModelServiceRegistryConfig(
            registry_name="custom_test_registry",
            lazy_loading_enabled=False,
            max_resolution_depth=20,
            health_monitoring_enabled=False,
            performance_monitoring_enabled=False,
        )

        # Act
        result = container.initialize_service_registry(config=custom_config)

        # Assert
        assert isinstance(result, ServiceRegistry)
        assert result.config.registry_name == "custom_test_registry"
        assert result.config.lazy_loading_enabled is False
        assert result.config.max_resolution_depth == 20
        assert result.config.health_monitoring_enabled is False
        assert result.config.performance_monitoring_enabled is False


@pytest.mark.unit
class TestInitializeServiceRegistryAlreadyInitialized:
    """Tests for initialize_service_registry when already initialized."""

    def test_initialize_service_registry_raises_if_already_initialized(self) -> None:
        """Verify initialize_service_registry raises error on second call.

        Calling initialize_service_registry twice should raise ModelOnexError
        with INVALID_STATE error code on the second call.
        """
        # Arrange
        container = ModelONEXContainer(enable_service_registry=False)
        container.initialize_service_registry()  # First call succeeds

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            container.initialize_service_registry()  # Second call fails

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE
        assert "already initialized" in exc_info.value.message.lower()


@pytest.mark.unit
class TestServiceRegistryPropertyNotInitialized:
    """Tests for service_registry property when not initialized."""

    def test_service_registry_property_raises_if_not_initialized(self) -> None:
        """Verify service_registry property raises error when not initialized.

        Accessing the service_registry property without calling
        initialize_service_registry should raise ModelOnexError with
        INVALID_STATE error code.
        """
        # Arrange
        container = ModelONEXContainer(enable_service_registry=False)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            _ = container.service_registry

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE
        assert "not initialized" in exc_info.value.message.lower()


@pytest.mark.unit
class TestInitializeServiceRegistryWhenAutoEnabled:
    """Tests for initialize_service_registry when auto-initialized by constructor."""

    def test_initialize_service_registry_when_already_enabled_in_constructor(
        self,
    ) -> None:
        """Verify initialize_service_registry raises error when auto-initialized.

        When enable_service_registry=True (the default), the constructor
        auto-initializes the registry. Calling initialize_service_registry
        afterward should raise ModelOnexError.
        """
        # Arrange
        container = ModelONEXContainer(enable_service_registry=True)

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            container.initialize_service_registry()

        assert exc_info.value.error_code == EnumCoreErrorCode.INVALID_STATE
        assert "already initialized" in exc_info.value.message.lower()


@pytest.mark.unit
class TestServiceRegistryPropertyAfterInitialize:
    """Tests for service_registry property after initialization."""

    def test_service_registry_property_works_after_initialize(self) -> None:
        """Verify service_registry property returns same instance consistently.

        After calling initialize_service_registry, subsequent accesses to
        the service_registry property should return the same ServiceRegistry
        instance.
        """
        # Arrange
        container = ModelONEXContainer(enable_service_registry=False)
        initialized_registry = container.initialize_service_registry()

        # Act
        first_access = container.service_registry
        second_access = container.service_registry
        third_access = container.service_registry

        # Assert
        assert first_access is initialized_registry
        assert second_access is initialized_registry
        assert third_access is initialized_registry


@pytest.mark.unit
class TestInitializeServiceRegistryReturnValue:
    """Tests for the return value of initialize_service_registry."""

    def test_initialize_service_registry_returns_same_as_property(self) -> None:
        """Verify initialize_service_registry return matches property access.

        The ServiceRegistry returned by initialize_service_registry should
        be the exact same instance returned by the service_registry property.
        """
        # Arrange
        container = ModelONEXContainer(enable_service_registry=False)

        # Act
        returned_registry = container.initialize_service_registry()
        property_registry = container.service_registry

        # Assert
        assert returned_registry is property_registry


@pytest.mark.unit
class TestInitializeServiceRegistryWithDefaultFactory:
    """Tests for initialize_service_registry using create_default_registry_config."""

    def test_initialize_matches_default_factory_config(self) -> None:
        """Verify default initialization matches create_default_registry_config.

        When initialize_service_registry is called without arguments, the
        resulting registry configuration should match what
        create_default_registry_config produces.
        """
        # Arrange
        container = ModelONEXContainer(enable_service_registry=False)
        expected_config = create_default_registry_config()

        # Act
        registry = container.initialize_service_registry()

        # Assert
        assert registry.config.registry_name == expected_config.registry_name
        assert (
            registry.config.lazy_loading_enabled == expected_config.lazy_loading_enabled
        )
        assert (
            registry.config.circular_dependency_detection
            == expected_config.circular_dependency_detection
        )
        assert (
            registry.config.max_resolution_depth == expected_config.max_resolution_depth
        )
