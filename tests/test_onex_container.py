"""
Test suite for ONEXContainer.

Tests the protocol-driven dependency injection container functionality.
"""

import pytest

from omnibase_core.core.onex_container import ModelONEXContainer as ONEXContainer
from omnibase_core.core.onex_container import (
    create_onex_container,
    get_container,
)
from omnibase_core.exceptions.base_onex_error import OnexError


class TestONEXContainer:
    """Test cases for ONEXContainer."""

    def test_container_initialization(self):
        """Test that container initializes correctly."""
        container = ONEXContainer()
        assert container._services == {}
        assert container._config == {}

    def test_service_registration(self):
        """Test service registration functionality."""
        container = ONEXContainer()
        mock_service = "mock_service_instance"

        container.register_service("ProtocolMock", mock_service)
        assert container.has_service("ProtocolMock")
        assert container.get_service("ProtocolMock") == mock_service

    def test_service_resolution_failure(self):
        """Test that missing services raise appropriate error."""
        container = ONEXContainer()

        with pytest.raises(OnexError) as exc_info:
            container.get_service("NonExistentProtocol")

        assert "Unable to resolve service" in str(exc_info.value)

    def test_protocol_shortcuts(self):
        """Test that protocol shortcuts work correctly."""
        container = ONEXContainer()
        mock_event_bus = "mock_event_bus"

        container.register_service("ProtocolEventBus", mock_event_bus)
        assert container.get_service("event_bus") == mock_event_bus

    def test_configuration(self):
        """Test container configuration."""
        container = ONEXContainer()
        config = {"test_key": "test_value"}

        container.configure(config)
        assert container._config["test_key"] == "test_value"

    def test_factory_function(self):
        """Test container factory function."""
        container = create_onex_container()
        assert isinstance(container, ONEXContainer)
        assert "logging" in container._config

    def test_global_container(self):
        """Test global container singleton."""
        container1 = get_container()
        container2 = get_container()
        assert container1 is container2
