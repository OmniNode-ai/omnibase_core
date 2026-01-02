"""Base dependency injection container using dependency-injector.

This module provides _BaseModelONEXContainer, a DeclarativeContainer that
defines the core service providers for the ONEX framework. It uses the
dependency-injector library to manage singleton and factory providers.

The container is wrapped by ModelONEXContainer which adds caching, logging,
and performance monitoring. This base container should not be used directly
in application code.

Providers:
    - config: Configuration provider for environment settings
    - enhanced_logger: Factory for ModelEnhancedLogger instances
    - workflow_factory: Factory for ModelWorkflowFactory instances
    - workflow_coordinator: Singleton ModelWorkflowCoordinator
    - action_registry: Singleton ModelActionRegistry with core actions
    - event_type_registry: Singleton ModelEventTypeRegistry with core types
    - command_registry: Singleton ModelCliCommandRegistry
    - secret_manager: Singleton ModelSecretManager

See Also:
    - ModelONEXContainer: Production container wrapping this base
    - dependency_injector: Third-party DI library used for providers
"""

from __future__ import annotations

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
    """Create enhanced logger with monadic patterns.

    Args:
        level: Logging level for the logger instance.

    Returns:
        Configured ModelEnhancedLogger instance.
    """
    return ModelEnhancedLogger(level)


def _create_workflow_factory() -> ModelWorkflowFactory:
    """Create workflow factory for LlamaIndex integration.

    Returns:
        New ModelWorkflowFactory instance for creating workflows.
    """
    return ModelWorkflowFactory()


def _create_workflow_coordinator(
    factory: ModelWorkflowFactory,
) -> ModelWorkflowCoordinator:
    """Create workflow execution coordinator.

    Args:
        factory: Workflow factory for creating new workflow instances.

    Returns:
        Configured ModelWorkflowCoordinator for executing workflows.
    """
    return ModelWorkflowCoordinator(factory)


def _create_action_registry() -> ModelActionRegistry:
    """Create action registry with core actions bootstrapped.

    Creates a new ModelActionRegistry and calls bootstrap_core_actions()
    to register built-in actions (help, version, etc.).

    Returns:
        ModelActionRegistry with core actions pre-registered.
    """
    registry = ModelActionRegistry()
    registry.bootstrap_core_actions()
    return registry


def _create_event_type_registry() -> ModelEventTypeRegistry:
    """Create event type registry with core event types bootstrapped.

    Creates a new ModelEventTypeRegistry and calls bootstrap_core_event_types()
    to register built-in event types.

    Returns:
        ModelEventTypeRegistry with core event types pre-registered.
    """
    registry = ModelEventTypeRegistry()
    registry.bootstrap_core_event_types()
    return registry


def _create_command_registry() -> ModelCliCommandRegistry:
    """Create command registry for CLI command discovery.

    Returns:
        Empty ModelCliCommandRegistry for registering CLI commands.
    """
    return ModelCliCommandRegistry()


def _create_secret_manager() -> ModelSecretManager:
    """Create secret manager with auto-configuration.

    Uses ModelSecretManager.create_auto_configured() to detect and configure
    the appropriate secrets backend (env vars, Vault, etc.).

    Returns:
        Auto-configured ModelSecretManager instance.
    """
    return ModelSecretManager.create_auto_configured()


class _BaseModelONEXContainer(containers.DeclarativeContainer):
    """Base dependency injection container using dependency-injector library.

    This is a DeclarativeContainer that defines providers for core ONEX services.
    It provides singleton and factory patterns for service instantiation.

    This class is internal and should not be instantiated directly. Use
    ModelONEXContainer or create_model_onex_container() instead.

    Providers:
        config: Configuration provider for runtime settings.
        enhanced_logger: Factory creating ModelEnhancedLogger instances.
        workflow_factory: Factory creating ModelWorkflowFactory instances.
        workflow_coordinator: Singleton ModelWorkflowCoordinator.
        action_registry: Singleton ModelActionRegistry with core actions.
        event_type_registry: Singleton ModelEventTypeRegistry with core types.
        command_registry: Singleton ModelCliCommandRegistry.
        secret_manager: Singleton ModelSecretManager.
    """

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
