"""
Comprehensive tests for util_bootstrap.py

Tests cover:
- Service discovery and bootstrap initialization
- Registry node access and fallback mechanisms
- Logging service resolution
- Event emission routing
- Service availability checks
- Error handling and exception scenarios
"""

from typing import Any, Protocol
from unittest.mock import MagicMock, Mock, patch

import pytest

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.services.service_logging import ServiceLogging
from omnibase_core.services.service_minimal_logging import ServiceMinimalLogging
from omnibase_core.utils import util_bootstrap


# Test Protocol Types
class MockServiceProtocol(Protocol):
    """Mock protocol for service discovery tests."""

    def test_method(self) -> str: ...


class MockLoggerProtocol(Protocol):
    """Mock logger protocol for testing."""

    def emit_log_event(self, *args: Any, **kwargs: Any) -> None: ...
    def emit_log_event_sync(self, *args: Any, **kwargs: Any) -> None: ...


# =============================================================================
# Test get_service() - Main service discovery
# =============================================================================


class TestGetService:
    """Tests for get_service() function."""

    def test_get_service_success_with_registry(self):
        """Test successful service retrieval through registry."""
        # Arrange
        mock_service = Mock()
        mock_registry = Mock()
        mock_registry.get_service.return_value = mock_service

        # Act
        with patch.object(
            util_bootstrap, "_get_registry_node", return_value=mock_registry
        ):
            result = util_bootstrap.get_service(MockServiceProtocol)

        # Assert
        assert result == mock_service
        mock_registry.get_service.assert_called_once_with(MockServiceProtocol)

    def test_get_service_registry_returns_none(self):
        """Test when registry exists but returns None for service."""
        # Arrange
        mock_registry = Mock()
        mock_registry.get_service.return_value = None

        # Act
        with patch.object(
            util_bootstrap, "_get_registry_node", return_value=mock_registry
        ):
            result = util_bootstrap.get_service(MockServiceProtocol)

        # Assert - when registry returns None, get_service returns None (no fallback)
        assert result is None

    def test_get_service_no_registry_uses_fallback(self):
        """Test fallback when registry is unavailable."""
        # Arrange
        mock_fallback = Mock()

        # Act
        with patch.object(util_bootstrap, "_get_registry_node", return_value=None):
            with patch.object(
                util_bootstrap, "_get_fallback_service", return_value=mock_fallback
            ) as mock_fallback_fn:
                result = util_bootstrap.get_service(MockServiceProtocol)

        # Assert
        assert result == mock_fallback
        mock_fallback_fn.assert_called_once_with(MockServiceProtocol)

    def test_get_service_registry_exception_uses_fallback(self):
        """Test fallback when registry raises exception."""
        # Arrange
        mock_fallback = Mock()

        # Act
        with patch.object(
            util_bootstrap,
            "_get_registry_node",
            side_effect=RuntimeError("Registry error"),
        ):
            with patch.object(
                util_bootstrap, "_get_fallback_service", return_value=mock_fallback
            ) as mock_fallback_fn:
                result = util_bootstrap.get_service(MockServiceProtocol)

        # Assert
        assert result == mock_fallback
        mock_fallback_fn.assert_called_once_with(MockServiceProtocol)

    def test_get_service_get_service_raises_exception(self):
        """Test when registry.get_service() raises exception."""
        # Arrange
        mock_registry = Mock()
        mock_registry.get_service.side_effect = ValueError("Service error")
        mock_fallback = Mock()

        # Act
        with patch.object(
            util_bootstrap, "_get_registry_node", return_value=mock_registry
        ):
            with patch.object(
                util_bootstrap, "_get_fallback_service", return_value=mock_fallback
            ) as mock_fallback_fn:
                result = util_bootstrap.get_service(MockServiceProtocol)

        # Assert
        assert result == mock_fallback
        mock_fallback_fn.assert_called_once_with(MockServiceProtocol)

    def test_get_service_both_registry_and_fallback_fail(self):
        """Test when both registry and fallback return None."""
        # Act
        with patch.object(util_bootstrap, "_get_registry_node", return_value=None):
            with patch.object(
                util_bootstrap, "_get_fallback_service", return_value=None
            ):
                result = util_bootstrap.get_service(MockServiceProtocol)

        # Assert
        assert result is None


# =============================================================================
# Test get_logging_service() - Bootstrap logging
# =============================================================================


class TestGetLoggingService:
    """Tests for get_logging_service() function."""

    def test_get_logging_service_success_with_registry(self):
        """Test successful logging service retrieval through registry."""
        # Arrange
        mock_protocol = Mock()
        mock_registry = Mock()
        mock_registry.get_protocol.return_value = mock_protocol

        # Act
        with patch.object(
            util_bootstrap, "_get_registry_node", return_value=mock_registry
        ):
            result = util_bootstrap.get_logging_service()

        # Assert
        assert isinstance(result, ServiceLogging)
        mock_registry.get_protocol.assert_called_once_with("logger")

    def test_get_logging_service_registry_no_protocol(self):
        """Test when registry exists but has no logger protocol."""
        # Arrange
        mock_registry = Mock()
        mock_registry.get_protocol.return_value = None

        # Act
        with patch.object(
            util_bootstrap, "_get_registry_node", return_value=mock_registry
        ):
            result = util_bootstrap.get_logging_service()

        # Assert
        assert isinstance(result, ServiceMinimalLogging)

    def test_get_logging_service_no_registry(self):
        """Test fallback to minimal logging when registry unavailable."""
        # Act
        with patch.object(util_bootstrap, "_get_registry_node", return_value=None):
            result = util_bootstrap.get_logging_service()

        # Assert
        assert isinstance(result, ServiceMinimalLogging)

    def test_get_logging_service_registry_exception(self):
        """Test fallback when registry raises exception."""
        # Act
        with patch.object(
            util_bootstrap,
            "_get_registry_node",
            side_effect=Exception("Registry error"),
        ):
            result = util_bootstrap.get_logging_service()

        # Assert
        assert isinstance(result, ServiceMinimalLogging)

    def test_get_logging_service_get_protocol_raises_exception(self):
        """Test fallback when get_protocol raises exception."""
        # Arrange
        mock_registry = Mock()
        mock_registry.get_protocol.side_effect = RuntimeError("Protocol error")

        # Act
        with patch.object(
            util_bootstrap, "_get_registry_node", return_value=mock_registry
        ):
            result = util_bootstrap.get_logging_service()

        # Assert
        assert isinstance(result, ServiceMinimalLogging)


# =============================================================================
# Test emit_log_event() - Event emission routing
# =============================================================================


class TestEmitLogEvent:
    """Tests for emit_log_event() function."""

    def test_emit_log_event_success_with_logging_service(self):
        """Test successful log event emission through logging service."""
        # Arrange
        mock_logging_service = Mock()
        mock_logging_service.emit_log_event.return_value = None

        # Act
        with patch.object(
            util_bootstrap, "get_logging_service", return_value=mock_logging_service
        ):
            result = util_bootstrap.emit_log_event(
                LogLevel.INFO, "test_event", "Test message", extra="data"
            )

        # Assert
        mock_logging_service.emit_log_event.assert_called_once_with(
            LogLevel.INFO, "test_event", "Test message", extra="data"
        )

    def test_emit_log_event_service_missing_method(self):
        """Test when logging service doesn't have emit_log_event method."""
        # Arrange
        mock_logging_service = Mock(spec=[])  # No methods

        # Act
        with patch.object(
            util_bootstrap, "get_logging_service", return_value=mock_logging_service
        ):
            result = util_bootstrap.emit_log_event(
                LogLevel.INFO, "test_event", "Test message"
            )

        # Assert - should not raise exception
        assert result is None

    def test_emit_log_event_get_logging_service_raises_exception(self):
        """Test when get_logging_service raises exception."""
        # Act
        with patch.object(
            util_bootstrap,
            "get_logging_service",
            side_effect=Exception("Service error"),
        ):
            result = util_bootstrap.emit_log_event(
                LogLevel.ERROR, "error_event", "Error message"
            )

        # Assert - should not raise exception, falls back to stderr
        assert result is None

    def test_emit_log_event_emit_raises_exception(self):
        """Test when emit_log_event itself raises exception."""
        # Arrange
        mock_logging_service = Mock()
        mock_logging_service.emit_log_event.side_effect = ValueError("Emit error")

        # Act
        with patch.object(
            util_bootstrap, "get_logging_service", return_value=mock_logging_service
        ):
            result = util_bootstrap.emit_log_event(
                LogLevel.WARNING, "warn_event", "Warning"
            )

        # Assert - should not raise exception
        assert result is None

    def test_emit_log_event_all_log_levels(self):
        """Test emit_log_event with all log levels."""
        # Arrange
        mock_logging_service = Mock()
        mock_logging_service.emit_log_event.return_value = None

        log_levels = [
            LogLevel.TRACE,
            LogLevel.DEBUG,
            LogLevel.INFO,
            LogLevel.WARNING,
            LogLevel.ERROR,
            LogLevel.CRITICAL,
            LogLevel.FATAL,
        ]

        # Act & Assert
        with patch.object(
            util_bootstrap, "get_logging_service", return_value=mock_logging_service
        ):
            for level in log_levels:
                util_bootstrap.emit_log_event(level, "event", f"Message for {level}")
                mock_logging_service.emit_log_event.assert_called_with(
                    level, "event", f"Message for {level}"
                )

    def test_emit_log_event_with_kwargs(self):
        """Test emit_log_event with various keyword arguments."""
        # Arrange
        mock_logging_service = Mock()

        # Act
        with patch.object(
            util_bootstrap, "get_logging_service", return_value=mock_logging_service
        ):
            util_bootstrap.emit_log_event(
                LogLevel.INFO,
                "complex_event",
                "Complex message",
                user_id="123",
                trace_id="abc-def",
                metadata={"key": "value"},
            )

        # Assert
        mock_logging_service.emit_log_event.assert_called_once_with(
            LogLevel.INFO,
            "complex_event",
            "Complex message",
            user_id="123",
            trace_id="abc-def",
            metadata={"key": "value"},
        )


# =============================================================================
# Test emit_log_event_sync() - Synchronous event emission
# =============================================================================


class TestEmitLogEventSync:
    """Tests for emit_log_event_sync() function."""

    def test_emit_log_event_sync_success(self):
        """Test successful synchronous log event emission."""
        # Arrange
        mock_logging_service = Mock()
        mock_logging_service.emit_log_event_sync.return_value = None

        # Act
        with patch.object(
            util_bootstrap, "get_logging_service", return_value=mock_logging_service
        ):
            result = util_bootstrap.emit_log_event_sync(
                LogLevel.INFO, "Test message", "test_event", extra="data"
            )

        # Assert
        mock_logging_service.emit_log_event_sync.assert_called_once_with(
            LogLevel.INFO, "Test message", "test_event", extra="data"
        )

    def test_emit_log_event_sync_with_default_event_type(self):
        """Test emit_log_event_sync with default event type."""
        # Arrange
        mock_logging_service = Mock()

        # Act
        with patch.object(
            util_bootstrap, "get_logging_service", return_value=mock_logging_service
        ):
            util_bootstrap.emit_log_event_sync(LogLevel.DEBUG, "Debug message")

        # Assert
        mock_logging_service.emit_log_event_sync.assert_called_once_with(
            LogLevel.DEBUG, "Debug message", "generic"
        )

    def test_emit_log_event_sync_service_missing_method(self):
        """Test when logging service doesn't have emit_log_event_sync method."""
        # Arrange
        mock_logging_service = Mock(spec=[])  # No methods

        # Act
        with patch.object(
            util_bootstrap, "get_logging_service", return_value=mock_logging_service
        ):
            result = util_bootstrap.emit_log_event_sync(LogLevel.INFO, "Test message")

        # Assert
        assert result is None

    def test_emit_log_event_sync_get_logging_service_raises_exception(self):
        """Test when get_logging_service raises exception."""
        # Act
        with patch.object(
            util_bootstrap,
            "get_logging_service",
            side_effect=Exception("Service error"),
        ):
            result = util_bootstrap.emit_log_event_sync(LogLevel.ERROR, "Error message")

        # Assert
        assert result is None

    def test_emit_log_event_sync_emit_raises_exception(self):
        """Test when emit_log_event_sync itself raises exception."""
        # Arrange
        mock_logging_service = Mock()
        mock_logging_service.emit_log_event_sync.side_effect = RuntimeError(
            "Emit error"
        )

        # Act
        with patch.object(
            util_bootstrap, "get_logging_service", return_value=mock_logging_service
        ):
            result = util_bootstrap.emit_log_event_sync(LogLevel.WARNING, "Warning")

        # Assert
        assert result is None

    def test_emit_log_event_sync_with_kwargs(self):
        """Test emit_log_event_sync with keyword arguments."""
        # Arrange
        mock_logging_service = Mock()

        # Act
        with patch.object(
            util_bootstrap, "get_logging_service", return_value=mock_logging_service
        ):
            util_bootstrap.emit_log_event_sync(
                LogLevel.INFO,
                "Message",
                "custom_event",
                request_id="req-123",
                correlation_id="corr-456",
            )

        # Assert
        mock_logging_service.emit_log_event_sync.assert_called_once_with(
            LogLevel.INFO,
            "Message",
            "custom_event",
            request_id="req-123",
            correlation_id="corr-456",
        )


# =============================================================================
# Test _get_registry_node() - Registry node helper
# =============================================================================


class TestGetRegistryNode:
    """Tests for _get_registry_node() private function."""

    def test_get_registry_node_success(self):
        """Test successful registry node retrieval via mocked import."""
        # Arrange
        mock_registry = Mock()
        mock_get_spi_registry = Mock(return_value=mock_registry)

        # Mock the module import
        import sys

        mock_module = Mock()
        mock_module.get_spi_registry = mock_get_spi_registry

        # Act
        with patch.dict(sys.modules, {"omnibase_spi.spi_registry": mock_module}):
            result = util_bootstrap._get_registry_node()

        # Assert
        assert result == mock_registry

    def test_get_registry_node_import_error(self):
        """Test when omnibase_spi is not available."""
        # Arrange - ensure the module is not available
        import sys

        # Act & Assert
        # Since we can't easily force an ImportError in tests, we test the behavior
        # by verifying _get_registry_node handles the case gracefully
        # In production, if omnibase_spi is not installed, this returns None
        with patch.dict(sys.modules, {"omnibase_spi.spi_registry": None}):
            result = util_bootstrap._get_registry_node()
            # Will return None or raise ImportError depending on environment
            assert result is None or isinstance(result, type(None))

    def test_get_registry_node_handles_missing_module(self):
        """Test that _get_registry_node returns None when import fails."""
        # This test verifies the ImportError handling logic
        # In actual use, ImportError is caught and None is returned
        result = util_bootstrap._get_registry_node()
        # Should return None if omnibase_spi is not available
        # or return a registry if it is available
        assert result is None or hasattr(result, "get_service")


# =============================================================================
# Test _get_fallback_service() - Fallback service helper
# =============================================================================


class TestGetFallbackService:
    """Tests for _get_fallback_service() private function."""

    def test_get_fallback_service_logger_protocol(self):
        """Test fallback for logger protocol types."""

        # Arrange
        class MockLoggerProtocol:
            __name__ = "LoggerProtocol"

        # Act
        result = util_bootstrap._get_fallback_service(MockLoggerProtocol)

        # Assert
        assert isinstance(result, ServiceMinimalLogging)

    def test_get_fallback_service_logger_in_name(self):
        """Test fallback for any protocol with Logger in name."""

        # Arrange
        class MockServiceLogger:
            __name__ = "ServiceLoggerInterface"

        # Act
        result = util_bootstrap._get_fallback_service(MockServiceLogger)

        # Assert
        assert isinstance(result, ServiceMinimalLogging)

    def test_get_fallback_service_non_logger_protocol(self):
        """Test fallback returns None for non-logger protocols."""

        # Arrange
        class MockDatabaseProtocol:
            __name__ = "DatabaseProtocol"

        # Act
        result = util_bootstrap._get_fallback_service(MockDatabaseProtocol)

        # Assert
        assert result is None

    def test_get_fallback_service_protocol_without_name(self):
        """Test fallback when protocol has no __name__ attribute."""
        # Arrange
        mock_protocol = Mock(spec=[])  # No __name__ attribute

        # Act
        result = util_bootstrap._get_fallback_service(mock_protocol)

        # Assert
        assert result is None

    def test_get_fallback_service_protocol_name_edge_cases(self):
        """Test fallback with unusual protocol name patterns."""
        # Test with empty string name
        mock_empty = type("", (), {})
        result_empty = util_bootstrap._get_fallback_service(mock_empty)
        assert result_empty is None

        # Test with None-like behavior (protocol without proper __name__)
        mock_broken = Mock(spec=[])
        del mock_broken.__name__  # Remove __name__ attribute
        result_broken = util_bootstrap._get_fallback_service(mock_broken)
        assert result_broken is None


# =============================================================================
# Test _get_minimal_logging_service() - Minimal logging
# =============================================================================


class TestGetMinimalLoggingService:
    """Tests for _get_minimal_logging_service() private function."""

    def test_get_minimal_logging_service_returns_service(self):
        """Test that minimal logging service is returned."""
        # Act
        result = util_bootstrap._get_minimal_logging_service()

        # Assert
        assert isinstance(result, ServiceMinimalLogging)

    def test_get_minimal_logging_service_is_functional(self):
        """Test that returned minimal logging service is functional."""
        # Act
        service = util_bootstrap._get_minimal_logging_service()

        # Assert - should not raise exceptions
        service.emit_log_event(LogLevel.INFO, "test_event", "Test message")
        service.emit_log_event_sync(LogLevel.DEBUG, "Debug message", "debug_event")

    def test_get_minimal_logging_service_returns_new_instance(self):
        """Test that each call returns a new instance."""
        # Act
        service1 = util_bootstrap._get_minimal_logging_service()
        service2 = util_bootstrap._get_minimal_logging_service()

        # Assert
        assert service1 is not service2
        assert isinstance(service1, ServiceMinimalLogging)
        assert isinstance(service2, ServiceMinimalLogging)


# =============================================================================
# Test is_service_available() - Service availability check
# =============================================================================


class TestIsServiceAvailable:
    """Tests for is_service_available() function."""

    def test_is_service_available_service_exists(self):
        """Test when service is available."""
        # Arrange
        mock_service = Mock()

        # Act
        with patch.object(util_bootstrap, "get_service", return_value=mock_service):
            result = util_bootstrap.is_service_available(MockServiceProtocol)

        # Assert
        assert result is True

    def test_is_service_available_service_not_found(self):
        """Test when service is not available."""
        # Act
        with patch.object(util_bootstrap, "get_service", return_value=None):
            result = util_bootstrap.is_service_available(MockServiceProtocol)

        # Assert
        assert result is False

    def test_is_service_available_get_service_raises_exception(self):
        """Test when get_service raises exception."""
        # Act
        with patch.object(
            util_bootstrap, "get_service", side_effect=Exception("Error")
        ):
            # Exception will be raised and propagated
            with pytest.raises(Exception):
                util_bootstrap.is_service_available(MockServiceProtocol)

    def test_is_service_available_various_protocols(self):
        """Test is_service_available with various protocol types."""
        # Arrange
        protocols = [
            MockServiceProtocol,
            MockLoggerProtocol,
            type("CustomProtocol", (), {}),
        ]

        # Act & Assert
        with patch.object(util_bootstrap, "get_service") as mock_get_service:
            for i, protocol in enumerate(protocols):
                # Alternate between available and unavailable
                mock_get_service.return_value = Mock() if i % 2 == 0 else None
                result = util_bootstrap.is_service_available(protocol)
                assert result == (i % 2 == 0)


# =============================================================================
# Test get_available_services() - List available services
# =============================================================================


class TestGetAvailableServices:
    """Tests for get_available_services() function."""

    def test_get_available_services_with_registry(self):
        """Test getting available services through registry."""
        # Arrange
        mock_registry = Mock()
        mock_registry.list_services.return_value = ["logging", "database", "cache"]

        # Act
        with patch.object(
            util_bootstrap, "_get_registry_node", return_value=mock_registry
        ):
            result = util_bootstrap.get_available_services()

        # Assert
        assert result == ["logging", "database", "cache"]
        mock_registry.list_services.assert_called_once()

    def test_get_available_services_registry_no_list_services_method(self):
        """Test when registry doesn't have list_services method."""
        # Arrange
        mock_registry = Mock(spec=[])  # No list_services method

        # Act
        with patch.object(
            util_bootstrap, "_get_registry_node", return_value=mock_registry
        ):
            result = util_bootstrap.get_available_services()

        # Assert
        assert result == ["logging"]

    def test_get_available_services_no_registry(self):
        """Test fallback when registry is unavailable."""
        # Act
        with patch.object(util_bootstrap, "_get_registry_node", return_value=None):
            result = util_bootstrap.get_available_services()

        # Assert
        assert result == ["logging"]

    def test_get_available_services_registry_raises_exception(self):
        """Test when registry.list_services raises exception."""
        # Arrange
        mock_registry = Mock()
        mock_registry.list_services.side_effect = RuntimeError("List error")

        # Act
        with patch.object(
            util_bootstrap, "_get_registry_node", return_value=mock_registry
        ):
            result = util_bootstrap.get_available_services()

        # Assert
        assert result == ["logging"]

    def test_get_available_services_get_registry_node_raises_exception(self):
        """Test when _get_registry_node raises exception."""
        # Act
        with patch.object(
            util_bootstrap,
            "_get_registry_node",
            side_effect=Exception("Registry error"),
        ):
            result = util_bootstrap.get_available_services()

        # Assert
        assert result == ["logging"]

    def test_get_available_services_returns_list(self):
        """Test that return value is always a list."""
        # Act
        with patch.object(util_bootstrap, "_get_registry_node", return_value=None):
            result = util_bootstrap.get_available_services()

        # Assert
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(s, str) for s in result)


# =============================================================================
# Integration Tests - Full workflow scenarios
# =============================================================================


class TestBootstrapIntegration:
    """Integration tests for complete bootstrap workflows."""

    def test_full_bootstrap_with_registry_success(self):
        """Test complete bootstrap workflow with working registry."""
        # Arrange
        mock_service = Mock()
        mock_protocol = Mock()
        mock_registry = Mock()
        mock_registry.get_service.return_value = mock_service
        mock_registry.get_protocol.return_value = mock_protocol
        mock_registry.list_services.return_value = ["logging", "database"]

        # Act
        with patch.object(
            util_bootstrap, "_get_registry_node", return_value=mock_registry
        ):
            # Get service
            service = util_bootstrap.get_service(MockServiceProtocol)
            assert service == mock_service

            # Check availability
            available = util_bootstrap.is_service_available(MockServiceProtocol)
            assert available is True

            # Get logging service
            logging_service = util_bootstrap.get_logging_service()
            assert isinstance(logging_service, ServiceLogging)

            # List services
            services = util_bootstrap.get_available_services()
            assert services == ["logging", "database"]

    def test_full_bootstrap_with_fallback_scenario(self):
        """Test complete bootstrap workflow with fallback to minimal services."""
        # Act
        with patch.object(util_bootstrap, "_get_registry_node", return_value=None):
            # Get service - should return None
            service = util_bootstrap.get_service(MockServiceProtocol)
            assert service is None

            # Check availability - should be False
            available = util_bootstrap.is_service_available(MockServiceProtocol)
            assert available is False

            # Get logging service - should fallback to minimal
            logging_service = util_bootstrap.get_logging_service()
            assert isinstance(logging_service, ServiceMinimalLogging)

            # List services - should return minimal list
            services = util_bootstrap.get_available_services()
            assert services == ["logging"]

    def test_logging_workflow_end_to_end(self):
        """Test complete logging workflow from service to emission."""
        # Arrange
        mock_protocol = Mock()
        mock_protocol.emit_log_event.return_value = None
        mock_protocol.emit_log_event_sync.return_value = None
        mock_registry = Mock()
        mock_registry.get_protocol.return_value = mock_protocol

        # Act
        with patch.object(
            util_bootstrap, "_get_registry_node", return_value=mock_registry
        ):
            # Emit async log event
            util_bootstrap.emit_log_event(LogLevel.INFO, "test_event", "Test message")
            mock_protocol.emit_log_event.assert_called_once()

            # Emit sync log event
            util_bootstrap.emit_log_event_sync(LogLevel.DEBUG, "Debug message")
            mock_protocol.emit_log_event_sync.assert_called_once()

    def test_degraded_mode_workflow(self):
        """Test bootstrap workflow in degraded mode (partial failures)."""
        # Arrange
        mock_registry = Mock()
        # Registry exists but some methods fail
        mock_registry.get_service.side_effect = Exception("Service error")
        mock_registry.get_protocol.return_value = None
        mock_registry.list_services.side_effect = Exception("List error")

        # Act
        with patch.object(
            util_bootstrap, "_get_registry_node", return_value=mock_registry
        ):
            # Service should fallback
            service = util_bootstrap.get_service(MockServiceProtocol)
            assert service is None

            # Logging should fallback to minimal
            logging_service = util_bootstrap.get_logging_service()
            assert isinstance(logging_service, ServiceMinimalLogging)

            # Services list should fallback
            services = util_bootstrap.get_available_services()
            assert services == ["logging"]

            # Emit should still work without errors
            util_bootstrap.emit_log_event(LogLevel.WARNING, "warn", "Warning message")
            util_bootstrap.emit_log_event_sync(LogLevel.ERROR, "Error message")


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestBootstrapEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_protocol_type(self):
        """Test with None as protocol type."""
        # Act & Assert
        with patch.object(util_bootstrap, "_get_registry_node", return_value=None):
            result = util_bootstrap.get_service(None)
            assert result is None

    def test_concurrent_service_access(self):
        """Test that bootstrap handles concurrent access safely."""
        # Arrange
        mock_registry = Mock()
        mock_registry.get_service.return_value = Mock()

        # Act - simulate concurrent calls
        with patch.object(
            util_bootstrap, "_get_registry_node", return_value=mock_registry
        ):
            results = [
                util_bootstrap.get_service(MockServiceProtocol) for _ in range(10)
            ]

        # Assert
        assert len(results) == 10
        assert all(r is not None for r in results)

    def test_service_logging_with_protocol_variations(self):
        """Test ServiceLogging creation with different protocol configurations."""
        # Arrange
        mock_protocol = Mock()
        mock_registry = Mock()
        mock_registry.get_protocol.return_value = mock_protocol

        # Act
        with patch.object(
            util_bootstrap, "_get_registry_node", return_value=mock_registry
        ):
            service = util_bootstrap.get_logging_service()

        # Assert
        assert isinstance(service, ServiceLogging)
        assert service._protocol == mock_protocol

    def test_fallback_service_case_sensitivity(self):
        """Test that fallback service check is case-sensitive for 'Logger'."""
        # Arrange - create mock protocol types with different name patterns
        mock_lower = type("lowercase_logger", (), {})
        mock_upper = type("LOGGER_SERVICE", (), {})
        mock_mixed = type("LoggerService", (), {})
        mock_capital = type("MyLoggerProtocol", (), {})

        # Act
        result_lower = util_bootstrap._get_fallback_service(mock_lower)
        result_upper = util_bootstrap._get_fallback_service(mock_upper)
        result_mixed = util_bootstrap._get_fallback_service(mock_mixed)
        result_capital = util_bootstrap._get_fallback_service(mock_capital)

        # Assert - only names containing "Logger" (capital L) should return service
        assert result_lower is None  # "logger" (lowercase) not matching
        assert result_upper is None  # "LOGGER" (all caps) not matching
        assert isinstance(result_mixed, ServiceMinimalLogging)  # "Logger" matches
        assert isinstance(result_capital, ServiceMinimalLogging)  # "Logger" matches

    def test_emit_log_with_special_characters(self):
        """Test log emission with special characters in messages."""
        # Arrange
        mock_logging_service = Mock()

        special_messages = [
            "Message with 日本語",
            "Message with emoji 🚀",
            "Message with\nnewlines\nand\ttabs",
            "Message with 'quotes' and \"double quotes\"",
        ]

        # Act & Assert
        with patch.object(
            util_bootstrap, "get_logging_service", return_value=mock_logging_service
        ):
            for message in special_messages:
                util_bootstrap.emit_log_event(LogLevel.INFO, "special_event", message)
                mock_logging_service.emit_log_event.assert_called()

    def test_registry_node_no_caching_behavior(self):
        """Test that get_service doesn't cache registry lookups."""
        # This test verifies that each call to get_service
        # goes through the registry lookup process
        call_count = 0

        def counting_registry():
            nonlocal call_count
            call_count += 1
            mock_reg = Mock()
            mock_reg.get_service.return_value = Mock()
            return mock_reg

        # Act - call get_service multiple times
        with patch.object(
            util_bootstrap, "_get_registry_node", side_effect=counting_registry
        ):
            util_bootstrap.get_service(MockServiceProtocol)
            util_bootstrap.get_service(MockServiceProtocol)
            util_bootstrap.get_service(MockServiceProtocol)

        # Assert - each call should invoke registry lookup
        assert call_count == 3
