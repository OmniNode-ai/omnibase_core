"""
Tests for ONEX Container service resolution functionality.

These tests address the critical test coverage gap identified in the PR review
for core framework components.
"""

from pathlib import Path
from typing import Protocol

import pytest

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.core.onex_container import ONEXContainer


class MockService(Protocol):
    """Mock service for testing service resolution."""

    def process(self, data: str) -> str:
        """Process data."""
        ...


class ConcreteService:
    """Concrete implementation of MockService."""

    def process(self, data: str) -> str:
        """Process data by adding prefix."""
        return f"processed: {data}"


class TestONEXContainer:
    """Test cases for ONEXContainer service resolution."""

    def test_container_initialization(self):
        """Test container can be initialized with empty registry."""
        container = ONEXContainer()
        assert container is not None
        assert container.registry == {}

    def test_register_service(self):
        """Test service registration works correctly."""
        container = ONEXContainer()
        service = ConcreteService()

        container.register_service("mock_service", service)

        assert "mock_service" in container.registry
        assert container.registry["mock_service"] is service

    def test_get_service_success(self):
        """Test successful service resolution."""
        container = ONEXContainer()
        service = ConcreteService()

        container.register_service("mock_service", service)
        resolved = container.get_service("mock_service")

        assert resolved is service
        assert resolved.process("test") == "processed: test"

    def test_get_service_not_found(self):
        """Test service resolution raises error when service not found."""
        container = ONEXContainer()

        with pytest.raises(OnexError) as exc_info:
            container.get_service("nonexistent_service")

        assert exc_info.value.error_code == CoreErrorCode.SERVICE_RESOLUTION_FAILED
        assert "Service 'nonexistent_service' not found" in str(exc_info.value)

    def test_get_service_with_protocol(self):
        """Test service resolution with protocol type checking."""
        container = ONEXContainer()
        service = ConcreteService()

        container.register_service("mock_service", service)
        resolved = container.get_service("mock_service", MockService)

        assert resolved is service
        # Verify protocol compliance
        assert hasattr(resolved, "process")
        assert callable(getattr(resolved, "process"))

    def test_register_service_overwrites_existing(self):
        """Test that registering a service with same name overwrites existing."""
        container = ONEXContainer()
        service1 = ConcreteService()
        service2 = ConcreteService()

        container.register_service("service", service1)
        container.register_service("service", service2)

        resolved = container.get_service("service")
        assert resolved is service2
        assert resolved is not service1

    def test_has_service(self):
        """Test service existence checking."""
        container = ONEXContainer()
        service = ConcreteService()

        assert not container.has_service("test_service")

        container.register_service("test_service", service)
        assert container.has_service("test_service")

    def test_clear_registry(self):
        """Test clearing all registered services."""
        container = ONEXContainer()
        service = ConcreteService()

        container.register_service("service1", service)
        container.register_service("service2", service)

        assert len(container.registry) == 2

        container.clear_registry()
        assert len(container.registry) == 0
        assert not container.has_service("service1")
        assert not container.has_service("service2")

    def test_service_lifecycle(self):
        """Test complete service lifecycle: register -> use -> clear."""
        container = ONEXContainer()
        service = ConcreteService()

        # Register
        container.register_service("lifecycle_service", service)
        assert container.has_service("lifecycle_service")

        # Use
        resolved = container.get_service("lifecycle_service")
        result = resolved.process("lifecycle_test")
        assert result == "processed: lifecycle_test"

        # Clear
        container.clear_registry()
        assert not container.has_service("lifecycle_service")

        with pytest.raises(OnexError):
            container.get_service("lifecycle_service")


if __name__ == "__main__":
    pytest.main([__file__])
