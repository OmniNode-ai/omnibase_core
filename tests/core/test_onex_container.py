"""
Comprehensive test suite for ONEXContainer.

Tests the protocol-driven dependency injection container functionality,
including service registration, protocol shortcuts, error handling, and
global container management.

This test suite uses the real production implementation via direct import
to eliminate code duplication while avoiding circular import issues.
"""

# Use real implementation to eliminate code duplication
import os
from typing import Protocol, TypeVar
from unittest.mock import patch

import pytest

from omnibase_core.core.core_error_codes import CoreErrorCode

# Import production implementation directly - no code duplication
from omnibase_core.core.onex_container import (
    ONEXContainer,
    create_onex_container,
    get_container,
)
from omnibase_core.exceptions.base_onex_error import OnexError

T = TypeVar("T")


# === TEST PROTOCOL DEFINITIONS ===


class ProtocolEventBus(Protocol):
    """Test protocol for event bus service."""

    def publish_event(self, event: str) -> None:
        """Publish an event."""
        ...


class ProtocolLogger(Protocol):
    """Test protocol for logging service."""

    def log(self, message: str) -> None:
        """Log a message."""
        ...


class ProtocolHealthCheck(Protocol):
    """Test protocol for health check service."""

    def check_health(self) -> bool:
        """Check system health."""
        ...


# === MOCK SERVICE IMPLEMENTATIONS ===


class MockEventBus:
    """Mock event bus implementation."""

    def __init__(self):
        self.events = []

    def publish_event(self, event: str) -> None:
        """Publish an event."""
        self.events.append(event)


class MockLogger:
    """Mock logger implementation."""

    def __init__(self):
        self.messages = []

    def log(self, message: str) -> None:
        """Log a message."""
        self.messages.append(message)


class MockHealthCheck:
    """Mock health check implementation."""

    def check_health(self) -> bool:
        """Check system health."""
        return True


# === TESTS ===


class TestONEXContainer:
    """Test cases for ONEXContainer core functionality."""

    def test_container_initialization(self):
        """Test that container initializes with empty services and config."""
        container = ONEXContainer()

        assert container._services == {}
        assert container._config == {}

    def test_service_registration(self):
        """Test basic service registration functionality."""
        container = ONEXContainer()
        mock_service = MockEventBus()
        protocol_name = "ProtocolEventBus"

        # Register service
        container.register_service(protocol_name, mock_service)

        # Verify registration
        assert container.has_service(protocol_name)
        assert container.get_service(protocol_name) is mock_service

    def test_service_retrieval_by_protocol_name(self):
        """Test service retrieval using full protocol names."""
        container = ONEXContainer()
        event_bus = MockEventBus()
        logger = MockLogger()
        health_check = MockHealthCheck()

        # Register services
        container.register_service("ProtocolEventBus", event_bus)
        container.register_service("ProtocolLogger", logger)
        container.register_service("ProtocolHealthCheck", health_check)

        # Verify retrieval
        assert container.get_service("ProtocolEventBus") is event_bus
        assert container.get_service("ProtocolLogger") is logger
        assert container.get_service("ProtocolHealthCheck") is health_check

    def test_protocol_shortcuts(self):
        """Test protocol shortcut resolution."""
        container = ONEXContainer()
        event_bus = MockEventBus()
        logger = MockLogger()
        health_check = MockHealthCheck()

        # Register services with full protocol names
        container.register_service("ProtocolEventBus", event_bus)
        container.register_service("ProtocolLogger", logger)
        container.register_service("ProtocolHealthCheck", health_check)

        # Test shortcut resolution
        assert container.get_service("event_bus") is event_bus
        assert container.get_service("logger") is logger
        assert container.get_service("health_check") is health_check

    def test_has_service_method(self):
        """Test has_service method for service existence checking."""
        container = ONEXContainer()
        mock_service = MockEventBus()

        # Test non-existent service
        assert not container.has_service("ProtocolEventBus")
        assert not container.has_service("NonExistentProtocol")

        # Register and test existing service
        container.register_service("ProtocolEventBus", mock_service)
        assert container.has_service("ProtocolEventBus")

        # Test that has_service only checks direct registration, not shortcuts
        assert not container.has_service(
            "event_bus"
        )  # Shortcut not checked by has_service

    def test_service_resolution_failure(self):
        """Test that missing services raise OnexError with correct error code."""
        container = ONEXContainer()

        # Test non-existent protocol
        with pytest.raises(OnexError) as exc_info:
            container.get_service("NonExistentProtocol")

        error = exc_info.value
        assert error.code == CoreErrorCode.SERVICE_RESOLUTION_FAILED
        assert (
            "Unable to resolve service for protocol: NonExistentProtocol"
            in error.message
        )

    def test_shortcut_resolution_failure(self):
        """Test that missing shortcut services raise OnexError."""
        container = ONEXContainer()

        # Test shortcut for non-registered service
        with pytest.raises(OnexError) as exc_info:
            container.get_service("event_bus")

        error = exc_info.value
        assert error.code == CoreErrorCode.SERVICE_RESOLUTION_FAILED
        assert "Unable to resolve service for protocol: event_bus" in error.message

    def test_configuration_method(self):
        """Test container configuration functionality."""
        container = ONEXContainer()

        # Test initial empty config
        assert container._config == {}

        # Test single configuration update
        config1 = {"database": {"host": "localhost", "port": 5432}}
        container.configure(config1)
        assert container._config["database"]["host"] == "localhost"
        assert container._config["database"]["port"] == 5432

        # Test configuration update (shallow merge behavior)
        # Note: dict.update() does shallow merge, so nested dicts are replaced
        config2 = {"logging": {"level": "DEBUG"}, "database": {"timeout": 30}}
        container.configure(config2)

        # Verify shallow merge behavior
        assert container._config["logging"]["level"] == "DEBUG"
        assert container._config["database"]["timeout"] == 30
        # The original database config is replaced, not merged
        assert "host" not in container._config["database"]  # Not preserved
        assert "port" not in container._config["database"]  # Not preserved

    def test_service_replacement(self):
        """Test that registering a service with the same name replaces the old one."""
        container = ONEXContainer()

        # Register first service
        service1 = MockEventBus()
        container.register_service("ProtocolEventBus", service1)
        assert container.get_service("ProtocolEventBus") is service1

        # Replace with second service
        service2 = MockEventBus()
        container.register_service("ProtocolEventBus", service2)
        assert container.get_service("ProtocolEventBus") is service2
        assert container.get_service("ProtocolEventBus") is not service1


class TestONEXContainerFactory:
    """Test cases for ONEXContainer factory functions."""

    @patch.dict(os.environ, {}, clear=True)
    def test_create_onex_container_default_config(self):
        """Test create_onex_container with default environment values."""
        container = create_onex_container()

        assert isinstance(container, ONEXContainer)
        assert container._config["logging"]["level"] == "INFO"
        assert container._config["environment"] == "development"

    @patch.dict(os.environ, {"LOG_LEVEL": "DEBUG", "ENVIRONMENT": "production"})
    def test_create_onex_container_custom_config(self):
        """Test create_onex_container with custom environment values."""
        container = create_onex_container()

        assert isinstance(container, ONEXContainer)
        assert container._config["logging"]["level"] == "DEBUG"
        assert container._config["environment"] == "production"

    @patch.dict(os.environ, {"LOG_LEVEL": "WARNING"})
    def test_create_onex_container_partial_env(self):
        """Test create_onex_container with partial environment configuration."""
        container = create_onex_container()

        assert isinstance(container, ONEXContainer)
        assert container._config["logging"]["level"] == "WARNING"
        assert container._config["environment"] == "development"  # Default


class TestGlobalContainer:
    """Test cases for global container instance management."""

    def setup_method(self):
        """Reset global container state before each test."""
        # Reset the global container in the real module
        onex_container_module._container = None

    def test_get_container_singleton(self):
        """Test that get_container returns the same instance."""
        container1 = get_container()
        container2 = get_container()

        assert container1 is container2
        assert isinstance(container1, ONEXContainer)

    def test_get_container_initialization(self):
        """Test that get_container properly initializes the container."""
        container = get_container()

        # Verify it's properly configured
        assert isinstance(container, ONEXContainer)
        assert "logging" in container._config
        assert "environment" in container._config

    @patch.dict(os.environ, {"LOG_LEVEL": "ERROR"})
    def test_get_container_respects_environment(self):
        """Test that get_container respects environment variables."""
        container = get_container()

        assert container._config["logging"]["level"] == "ERROR"


class TestDependencyInjectionPatterns:
    """Test cases for protocol-based dependency injection patterns."""

    def test_protocol_based_service_usage(self):
        """Test that services can be used through their protocol interfaces."""
        container = ONEXContainer()

        # Register concrete implementations
        event_bus = MockEventBus()
        logger = MockLogger()

        container.register_service("ProtocolEventBus", event_bus)
        container.register_service("ProtocolLogger", logger)

        # Use services through protocol interface
        bus_service = container.get_service("ProtocolEventBus")
        log_service = container.get_service("ProtocolLogger")

        # Test protocol methods
        bus_service.publish_event("test_event")
        log_service.log("test_message")

        # Verify behavior
        assert "test_event" in event_bus.events
        assert "test_message" in logger.messages

    def test_mixed_protocol_and_shortcut_usage(self):
        """Test using both full protocol names and shortcuts."""
        container = ONEXContainer()
        event_bus = MockEventBus()

        container.register_service("ProtocolEventBus", event_bus)

        # Both should return the same instance
        service1 = container.get_service("ProtocolEventBus")
        service2 = container.get_service("event_bus")

        assert service1 is service2
        assert service1 is event_bus

    def test_service_isolation(self):
        """Test that different service instances are properly isolated."""
        container = ONEXContainer()

        bus1 = MockEventBus()
        bus2 = MockEventBus()

        container.register_service("ProtocolEventBus", bus1)
        container.register_service("ProtocolCustomBus", bus2)

        # Use services independently
        container.get_service("ProtocolEventBus").publish_event("event1")
        container.get_service("ProtocolCustomBus").publish_event("event2")

        # Verify isolation
        assert "event1" in bus1.events
        assert "event1" not in bus2.events
        assert "event2" in bus2.events
        assert "event2" not in bus1.events


class TestErrorHandling:
    """Test cases for error handling and edge cases."""

    def test_empty_protocol_name(self):
        """Test handling of empty protocol name."""
        container = ONEXContainer()

        with pytest.raises(OnexError) as exc_info:
            container.get_service("")

        assert exc_info.value.code == CoreErrorCode.SERVICE_RESOLUTION_FAILED

    def test_none_service_registration(self):
        """Test that None can be registered as a service (valid use case)."""
        container = ONEXContainer()

        container.register_service("ProtocolNull", None)
        assert container.has_service("ProtocolNull")
        assert container.get_service("ProtocolNull") is None

    def test_service_registration_overwrites(self):
        """Test that service registration properly overwrites existing services."""
        container = ONEXContainer()

        service1 = MockEventBus()
        service2 = MockLogger()

        container.register_service("TestProtocol", service1)
        assert container.get_service("TestProtocol") is service1

        # Overwrite with different service
        container.register_service("TestProtocol", service2)
        assert container.get_service("TestProtocol") is service2
        assert container.get_service("TestProtocol") is not service1


class TestIntegration:
    """Integration test cases combining multiple container features."""

    def test_full_container_lifecycle(self):
        """Test complete container usage lifecycle."""
        # Create container
        container = ONEXContainer()

        # Configure
        config = {
            "app": {"name": "test_app"},
            "features": {"logging": True, "health_checks": True},
        }
        container.configure(config)

        # Register services
        event_bus = MockEventBus()
        logger = MockLogger()
        health_check = MockHealthCheck()

        container.register_service("ProtocolEventBus", event_bus)
        container.register_service("ProtocolLogger", logger)
        container.register_service("ProtocolHealthCheck", health_check)

        # Use services through various access patterns
        container.get_service("ProtocolEventBus").publish_event("app_started")
        container.get_service("logger").log("Application initialized")
        health_status = container.get_service("health_check").check_health()

        # Verify integration
        assert "app_started" in event_bus.events
        assert "Application initialized" in logger.messages
        assert health_status is True
        assert container._config["app"]["name"] == "test_app"

    def test_factory_and_global_container_integration(self):
        """Test integration between factory function and global container."""
        # Reset global state
        global _container
        _container = None

        # Create using factory
        factory_container = create_onex_container()

        # Get global container (should be different instance)
        global_container = get_container()

        # They should be different instances
        assert factory_container is not global_container

        # But both should be properly configured
        assert "logging" in factory_container._config
        assert "logging" in global_container._config

    def test_multiple_protocol_shortcuts(self):
        """Test all protocol shortcuts work correctly."""
        container = ONEXContainer()

        # Register all shortcut services
        event_bus = MockEventBus()
        logger = MockLogger()
        health_check = MockHealthCheck()

        container.register_service("ProtocolEventBus", event_bus)
        container.register_service("ProtocolLogger", logger)
        container.register_service("ProtocolHealthCheck", health_check)

        # Test all shortcuts
        shortcuts = {
            "event_bus": event_bus,
            "logger": logger,
            "health_check": health_check,
        }

        for shortcut, expected_service in shortcuts.items():
            assert container.get_service(shortcut) is expected_service


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
