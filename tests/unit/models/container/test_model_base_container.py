"""Tests for base container helper functions."""

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.models.container.model_base_model_onex_container import (
    _create_action_registry,
    _create_command_registry,
    _create_enhanced_logger,
    _create_event_type_registry,
    _create_secret_manager,
    _create_workflow_coordinator,
    _create_workflow_factory,
)


class TestBaseContainerHelpers:
    """Tests for base container helper functions."""

    def test_create_enhanced_logger(self):
        """Test enhanced logger creation."""
        logger = _create_enhanced_logger(LogLevel.INFO)
        assert logger is not None
        assert logger.level == LogLevel.INFO

    def test_create_enhanced_logger_various_levels(self):
        """Test logger creation with different levels."""
        for level in [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR]:
            logger = _create_enhanced_logger(level)
            assert logger.level == level

    def test_create_workflow_factory(self):
        """Test workflow factory creation."""
        factory = _create_workflow_factory()
        assert factory is not None
        workflows = factory.list_available_workflows()
        assert len(workflows) > 0

    def test_create_workflow_coordinator(self):
        """Test workflow coordinator creation."""
        factory = _create_workflow_factory()
        coordinator = _create_workflow_coordinator(factory)
        assert coordinator is not None
        assert coordinator.factory == factory

    def test_create_action_registry(self):
        """Test action registry creation."""
        registry = _create_action_registry()
        assert registry is not None
        # Registry should be initialized

    def test_create_event_type_registry(self):
        """Test event type registry creation."""
        registry = _create_event_type_registry()
        assert registry is not None
        # Registry should be initialized

    def test_create_command_registry(self):
        """Test command registry creation."""
        registry = _create_command_registry()
        assert registry is not None
        # Registry should be initialized

    def test_create_secret_manager(self):
        """Test secret manager creation."""
        manager = _create_secret_manager()
        assert manager is not None
        # Secret manager should be initialized

    def test_coordinator_with_factory_integration(self):
        """Test coordinator properly integrates with factory."""
        factory = _create_workflow_factory()
        coordinator = _create_workflow_coordinator(factory)

        # Coordinator should use the factory
        assert coordinator.factory is factory

        # Factory should list workflows
        workflows = factory.list_available_workflows()
        assert "simple_sequential" in workflows

    def test_registries_are_independent(self):
        """Test that each registry creation is independent."""
        registry1 = _create_action_registry()
        registry2 = _create_action_registry()

        # Should be different instances
        assert registry1 is not registry2

    def test_logger_levels_hierarchy(self):
        """Test logger creation respects level hierarchy."""
        debug_logger = _create_enhanced_logger(LogLevel.DEBUG)
        info_logger = _create_enhanced_logger(LogLevel.INFO)
        warning_logger = _create_enhanced_logger(LogLevel.WARNING)
        error_logger = _create_enhanced_logger(LogLevel.ERROR)

        # Each logger maintains its configured level
        assert debug_logger.level == LogLevel.DEBUG
        assert info_logger.level == LogLevel.INFO
        assert warning_logger.level == LogLevel.WARNING
        assert error_logger.level == LogLevel.ERROR
