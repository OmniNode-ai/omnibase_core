"""
Test suite for ONEX node services.

Tests the base classes for EFFECT, COMPUTE, REDUCER, and ORCHESTRATOR nodes.
"""

import pytest

from omnibase_core.core.onex_container import ONEXContainer


class TestNodeServices:
    """Test cases for node service base classes."""

    def test_node_base_initialization(self):
        """Test that node services can be initialized with container."""
        container = ONEXContainer()

        # Note: Actual node service tests would require importing the base classes
        # These tests will be expanded once omnibase-spi dependency is available
        assert container is not None

    def test_container_dependency_injection(self):
        """Test that nodes receive container dependency correctly."""
        container = ONEXContainer()

        # Mock service registration for testing
        mock_logger = "mock_logger_service"
        container.register_service("ProtocolLogger", mock_logger)

        # Verify service can be resolved
        assert container.get_service("ProtocolLogger") == mock_logger
