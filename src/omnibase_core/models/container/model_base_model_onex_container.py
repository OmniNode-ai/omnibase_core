"""
Base dependency injection container.
"""

from __future__ import annotations

from typing import Any

from dependency_injector import containers, providers

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.models.core.model_action_registry import ModelActionRegistry
from omnibase_core.models.core.model_cli_command_registry import ModelCliCommandRegistry
from omnibase_core.models.core.model_event_type_registry import ModelEventTypeRegistry
from omnibase_core.models.security.model_secret_manager import ModelSecretManager

from .model_enhanced_logger import ModelEnhancedLogger
from .model_workflow_coordinator import ModelWorkflowCoordinator
from .model_workflow_factory import ModelWorkflowFactory


def _create_enhanced_logger(level: LogLevel) -> ModelEnhancedLogger:
    """Create enhanced logger with monadic patterns."""
    return ModelEnhancedLogger(level)


def _create_workflow_factory() -> ModelWorkflowFactory:
    """Create workflow factory for LlamaIndex integration."""
    return ModelWorkflowFactory()


def _create_workflow_coordinator(factory: Any) -> ModelWorkflowCoordinator:
    """Create workflow execution coordinator."""
    return ModelWorkflowCoordinator(factory)


def _create_action_registry() -> ModelActionRegistry:
    """Create action registry with core actions bootstrapped."""
    registry = ModelActionRegistry()
    registry.bootstrap_core_actions()
    return registry


def _create_event_type_registry() -> ModelEventTypeRegistry:
    """Create event type registry with core event types bootstrapped."""
    registry = ModelEventTypeRegistry()
    registry.bootstrap_core_event_types()
    return registry


def _create_command_registry() -> ModelCliCommandRegistry:
    """Create command registry."""
    return ModelCliCommandRegistry()


def _create_secret_manager() -> ModelSecretManager:
    """Create secret manager with auto-configuration."""
    return ModelSecretManager.create_auto_configured()


class _BaseModelONEXContainer(containers.DeclarativeContainer):
    """Base dependency injection container."""

    # === CONFIGURATION ===
    config = providers.Configuration()

    # === ENHANCED CORE SERVICES ===

    # Enhanced logger with monadic patterns
    enhanced_logger = providers.Factory(
        lambda level: _create_enhanced_logger(level),
        level=LogLevel.INFO,
    )

    # === WORKFLOW ORCHESTRATION ===

    # LlamaIndex workflow factory
    workflow_factory = providers.Factory(lambda: _create_workflow_factory())

    # Workflow execution coordinator
    workflow_coordinator = providers.Singleton(
        lambda factory: _create_workflow_coordinator(factory),
        factory=workflow_factory,
    )

    # === REGISTRIES ===

    # Action registry for dynamic CLI actions
    action_registry = providers.Singleton(lambda: _create_action_registry())

    # Event type registry for dynamic event types
    event_type_registry = providers.Singleton(lambda: _create_event_type_registry())

    # Command registry for CLI command discovery
    command_registry = providers.Singleton(lambda: _create_command_registry())

    # === SECURITY ===

    # Secret manager for credential management
    secret_manager = providers.Singleton(lambda: _create_secret_manager())


__all__ = []
